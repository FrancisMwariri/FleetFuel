from fastapi import APIRouter

from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.assignments import router as assignments_router
from app.api.v1.endpoints.attachments import router as attachments_router
from app.api.v1.endpoints.audit_logs import router as audit_logs_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.drivers import router as drivers_router
from app.api.v1.endpoints.fuel_records import router as fuel_records_router
from app.api.v1.endpoints.invitations import router as invitations_router
from app.api.v1.endpoints.organizations import router as organizations_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.sync import router as sync_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.vehicles import router as vehicles_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(vehicles_router)
api_router.include_router(drivers_router)
api_router.include_router(assignments_router)
api_router.include_router(fuel_records_router)
api_router.include_router(sync_router)
api_router.include_router(attachments_router)
api_router.include_router(analytics_router)
api_router.include_router(alerts_router)
api_router.include_router(dashboard_router)
api_router.include_router(audit_logs_router)
api_router.include_router(reports_router)
api_router.include_router(organizations_router)
api_router.include_router(invitations_router)
api_router.include_router(users_router)
