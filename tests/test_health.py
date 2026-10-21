from fastapi.testclient import TestClient

from app.api.v1.endpoints import ready
from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_service_unavailable_without_database(monkeypatch) -> None:
    def no_database() -> None:
        raise RuntimeError("FLEETFUEL_DATABASE_URL must be configured")

    monkeypatch.setattr(ready, "get_engine", no_database)
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}
