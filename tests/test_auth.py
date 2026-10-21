import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import auth as auth_endpoint
from app.models.entities import Organization, User


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_and_current_user(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, organization, user = api_client
    token = login(client)

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "organization_id": str(organization.id),
        "email": "admin@example.com",
        "full_name": "Test Admin",
        "role": "ORG_ADMIN",
        "is_active": True,
    }


def test_invalid_password_is_rejected(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, _, _ = api_client
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_current_user_requires_valid_token(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, _, _ = api_client
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


def test_logout_revokes_access_token(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, _, _ = api_client
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    logout_response = client.post("/api/v1/auth/logout", headers=headers)
    current_user_response = client.get("/api/v1/auth/me", headers=headers)

    assert logout_response.status_code == 204
    assert current_user_response.status_code == 401


def test_password_reset_is_one_time_and_revokes_sessions(
    api_client: tuple[TestClient, Session, Organization, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _, _ = api_client
    old_token = login(client)
    sent: dict[str, str] = {}

    def capture_email(email: str, token: str) -> bool:
        sent["email"] = email
        sent["token"] = token
        return True

    monkeypatch.setattr(auth_endpoint, "send_password_reset_email", capture_email)
    unknown = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "unknown@example.com"}
    )
    requested = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "admin@example.com"}
    )
    assert unknown.status_code == requested.status_code == 202
    assert unknown.json() == requested.json()
    assert sent["email"] == "admin@example.com"

    reset_payload = {"token": sent["token"], "new_password": "changed-test-password"}
    confirmed = client.post("/api/v1/auth/password-reset/confirm", json=reset_payload)
    replay = client.post("/api/v1/auth/password-reset/confirm", json=reset_payload)
    old_session = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "changed-test-password"},
    )

    assert confirmed.status_code == 204
    assert replay.status_code == 400
    assert old_session.status_code == 401
    assert new_login.status_code == 200


def test_login_rate_limit(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, _, _ = api_client
    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )

    assert limited.status_code == 429
