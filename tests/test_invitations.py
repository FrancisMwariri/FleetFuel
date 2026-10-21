from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.entities import AuthSession, Driver, Organization, User


def test_org_admin_invitation_registers_user_once(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, _, _ = api_client
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invitation = client.post(
        "/api/v1/organizations/invitations",
        json={"email": "driver@example.com", "role": "DRIVER"},
        headers=headers,
    )
    assert invitation.status_code == 201
    invite_token = invitation.json()["invitation_token"]

    registered = client.post(
        "/api/v1/organizations/invitations/register",
        json={
            "invitation_token": invite_token,
            "full_name": "Fleet Driver",
            "password": "a-strong-test-password",
        },
    )
    replay = client.post(
        "/api/v1/organizations/invitations/register",
        json={
            "invitation_token": invite_token,
            "full_name": "Fleet Driver",
            "password": "a-strong-test-password",
        },
    )

    assert registered.status_code == 201
    assert replay.status_code == 400
    driver = session.scalar(select(Driver).where(Driver.email == "driver@example.com"))
    assert driver is not None
    assert driver.user_id is not None
    user_response = client.post(
        "/api/v1/auth/login",
        json={"email": "driver@example.com", "password": "a-strong-test-password"},
    )
    assert user_response.status_code == 200
    assert user_response.json()["access_token"]

    driver_headers = {"Authorization": f"Bearer {user_response.json()['access_token']}"}
    forbidden_invitation = client.post(
        "/api/v1/organizations/invitations",
        json={"email": "another@example.com", "role": "VIEWER"},
        headers=driver_headers,
    )
    assert forbidden_invitation.status_code == 403


def test_driver_cannot_invite_users(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, _, _, _ = api_client
    invitation = client.post(
        "/api/v1/organizations/invitations",
        json={"email": "driver@example.com", "role": "DRIVER"},
        headers={"Authorization": "Bearer invalid"},
    )
    assert invitation.status_code == 401


def test_platform_admin_can_suspend_organization(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    organization_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    organization_token = organization_login.json()["access_token"]
    platform_admin = User(
        organization_id=None,
        email="platform@example.com",
        password_hash=hash_password("platform-test-password"),
        full_name="Platform Admin",
        role="SUPER_ADMIN",
    )
    session.add(platform_admin)
    session.flush()
    token, session_id, expires_at = create_access_token(platform_admin.id)
    session.add(AuthSession(id=session_id, user_id=platform_admin.id, expires_at=expires_at))
    session.commit()

    response = client.patch(
        f"/api/v1/organizations/{organization.id}",
        json={"status": "SUSPENDED", "reason": "Organization requested a pause"},
        headers={"Authorization": f"Bearer {token}"},
    )
    vehicles = client.get(
        "/api/v1/vehicles",
        headers={"Authorization": f"Bearer {organization_token}"},
    )
    suspended_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUSPENDED"
    assert vehicles.status_code == 401
    assert suspended_login.status_code == 401
