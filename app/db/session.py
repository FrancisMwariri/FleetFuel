from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("FLEETFUEL_DATABASE_URL must be configured")
    return create_engine(database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Generator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def dispose_database() -> None:
    try:
        engine = get_engine()
    except RuntimeError:
        return
    engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
