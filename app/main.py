import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.ready import router as ready_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.request_context import request_id_context
from app.db.session import dispose_database

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    dispose_database()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)


@app.middleware("http")
async def request_context_middleware(request, call_next):
    requested_id = request.headers.get("X-Request-ID", "")
    request_id = (
        requested_id if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", requested_id) else str(uuid4())
    )
    token = request_id_context.set(request_id)
    started_at = perf_counter()
    try:
        response = await call_next(request)
    finally:
        request_id_context.reset(token)
    response.headers["X-Request-ID"] = request_id
    logging.getLogger("fleetfuel.access").info(
        "request_complete method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - started_at) * 1000,
        request_id,
    )
    return response


if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

app.include_router(health_router)
app.include_router(ready_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
