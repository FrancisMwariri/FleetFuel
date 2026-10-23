import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgres://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
        ("postgresql://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
        (
            "postgresql+psycopg://user:pass@host/db",
            "postgresql+psycopg://user:pass@host/db",
        ),
    ],
)
def test_database_url_uses_installed_psycopg_driver(database_url: str, expected: str) -> None:
    settings = Settings(database_url=database_url, _env_file=None)

    assert settings.database_url == expected


def test_production_api_docs_require_explicit_opt_in() -> None:
    required_production_settings = {
        "environment": "production",
        "database_url": "postgresql+psycopg://user:password@localhost/fleetfuel",
        "jwt_secret": "test-secret-with-at-least-32-characters",
        "_env_file": None,
    }
    defaults = Settings(**required_production_settings)
    enabled = Settings(**required_production_settings, enable_docs=True)

    assert defaults.docs_enabled is False
    assert enabled.docs_enabled is True
