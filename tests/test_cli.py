from collections.abc import Callable

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import cli
from app.db.base import Base
from app.models.entities import Organization, User


@pytest.fixture
def bootstrap_database(monkeypatch: pytest.MonkeyPatch) -> Callable[[], sessionmaker[Session]]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(cli, "get_session_factory", lambda: factory)
    monkeypatch.setenv("FLEETFUEL_BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("FLEETFUEL_BOOTSTRAP_ADMIN_PASSWORD", "strong-password-123")
    monkeypatch.setenv("FLEETFUEL_BOOTSTRAP_ORGANIZATION", "MediFuel Demo Fleet")
    monkeypatch.setenv("FLEETFUEL_BOOTSTRAP_CURRENCY", "KES")
    yield lambda: factory
    engine.dispose()


def test_bootstrap_admin_creates_fleet_admin_when_database_is_empty(
    bootstrap_database: Callable[[], sessionmaker[Session]],
) -> None:
    cli.bootstrap_admin()

    with bootstrap_database()() as session:
        user = session.scalar(select(User).where(User.email == "admin@example.com"))
        organization = session.get(Organization, user.organization_id)
        assert user.role == "ORG_ADMIN"
        assert organization.name == "MediFuel Demo Fleet"
        assert organization.default_currency == "KES"


def test_bootstrap_admin_assigns_existing_platform_admin_to_fleet(
    bootstrap_database: Callable[[], sessionmaker[Session]],
) -> None:
    with bootstrap_database()() as session:
        session.add(
            User(
                organization_id=None,
                email="admin@example.com",
                password_hash="existing-password-hash",
                full_name="Platform Administrator",
                role="SUPER_ADMIN",
            )
        )
        session.commit()

    cli.bootstrap_admin()
    cli.bootstrap_admin()

    with bootstrap_database()() as session:
        user = session.scalar(select(User).where(User.email == "admin@example.com"))
        organizations = list(session.scalars(select(Organization)))
        assert user.role == "ORG_ADMIN"
        assert user.organization_id == organizations[0].id
        assert len(organizations) == 1


def test_bootstrap_admin_does_not_change_an_unrelated_account(
    bootstrap_database: Callable[[], sessionmaker[Session]],
) -> None:
    with bootstrap_database()() as session:
        session.add(
            User(
                organization_id=None,
                email="other@example.com",
                password_hash="existing-password-hash",
                full_name="Other Administrator",
                role="SUPER_ADMIN",
            )
        )
        session.commit()

    with pytest.raises(RuntimeError, match="only allowed when no users exist"):
        cli.bootstrap_admin()
