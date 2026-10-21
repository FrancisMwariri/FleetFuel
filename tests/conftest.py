import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import Organization, User


@pytest.fixture
def api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, Session, Organization, User]]:
    monkeypatch.setenv("FLEETFUEL_JWT_SECRET", "test-only-secret-that-is-long-enough")
    get_settings.cache_clear()
    test_database_url = os.getenv("FLEETFUEL_TEST_DATABASE_URL")
    if test_database_url:
        if not (make_url(test_database_url).database or "").endswith("_test"):
            pytest.fail("FLEETFUEL_TEST_DATABASE_URL must point to a database ending in _test")
        engine = create_engine(test_database_url, pool_pre_ping=True)
        connection = engine.connect()
        outer_transaction = connection.begin()
        session = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection: object, _: object) -> None:
            cursor = connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        connection = None
        outer_transaction = None
        session = Session(engine, expire_on_commit=False)

    Base.metadata.create_all(engine)
    organization = Organization(name="Test Fleet", slug="test-fleet", default_currency="USD")
    session.add(organization)
    session.flush()
    user = User(
        organization_id=organization.id,
        email="admin@example.com",
        password_hash=hash_password("test-password-123"),
        full_name="Test Admin",
        role="ORG_ADMIN",
    )
    session.add(user)
    session.commit()

    def override_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client, session, organization, user
    finally:
        app.dependency_overrides.clear()
        session.close()
        if outer_transaction is not None:
            outer_transaction.rollback()
        if connection is not None:
            connection.close()
        engine.dispose()
        get_settings.cache_clear()
