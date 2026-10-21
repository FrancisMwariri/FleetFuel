from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Organization, User


def test_fuel_date_filters_require_timezone(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, _, _ = api_client
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(
        "/api/v1/fuel-records?purchased_from=2026-10-20T10:00:00",
        headers=headers,
    )

    assert response.status_code == 422
