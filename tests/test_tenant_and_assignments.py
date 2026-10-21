from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.entities import AuthSession, Driver, Organization, User, Vehicle, VehicleAssignment


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_vehicle_access_is_scoped_to_authenticated_organization(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    visible_vehicle = Vehicle(
        organization_id=organization.id,
        registration_number="ORG-A-1",
        fuel_type="DIESEL",
    )
    other_organization = Organization(
        name="Other Fleet",
        slug="other-fleet",
        default_currency="USD",
    )
    session.add_all([visible_vehicle, other_organization])
    session.flush()
    hidden_vehicle = Vehicle(
        organization_id=other_organization.id,
        registration_number="ORG-B-1",
        fuel_type="DIESEL",
    )
    session.add(hidden_vehicle)
    session.commit()
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    visible = client.get(f"/api/v1/vehicles/{visible_vehicle.id}", headers=headers)
    hidden = client.get(f"/api/v1/vehicles/{hidden_vehicle.id}", headers=headers)
    listing = client.get("/api/v1/vehicles", headers=headers)

    assert visible.status_code == 200
    assert hidden.status_code == 404
    assert [item["id"] for item in listing.json()] == [str(visible_vehicle.id)]


def test_active_assignment_is_exclusive_and_can_be_ended(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = Vehicle(
        organization_id=organization.id,
        registration_number="ASSIGN-1",
        fuel_type="DIESEL",
    )
    driver = Driver(organization_id=organization.id, full_name="Assigned Driver")
    session.add_all([vehicle, driver])
    session.commit()
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    assignment_payload = {"vehicle_id": str(vehicle.id), "driver_id": str(driver.id)}

    assigned = client.post("/api/v1/assignments", json=assignment_payload, headers=headers)
    conflict = client.post("/api/v1/assignments", json=assignment_payload, headers=headers)
    ended = client.post(f"/api/v1/assignments/{assigned.json()['id']}/end", headers=headers)
    assigned_again = client.post("/api/v1/assignments", json=assignment_payload, headers=headers)

    assert assigned.status_code == 201
    assert conflict.status_code == 409
    assert ended.status_code == 200
    assert assigned_again.status_code == 201


def test_driver_can_use_only_assigned_vehicle(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, administrator = api_client
    assigned_vehicle = Vehicle(
        organization_id=organization.id,
        registration_number="DRIVER-ASSIGNED",
        fuel_type="DIESEL",
    )
    unassigned_vehicle = Vehicle(
        organization_id=organization.id,
        registration_number="DRIVER-OTHER",
        fuel_type="DIESEL",
    )
    driver_user = User(
        organization_id=organization.id,
        email="assigned-driver@example.com",
        password_hash=hash_password("driver-test-password"),
        full_name="Assigned Driver",
        role="DRIVER",
    )
    session.add_all([assigned_vehicle, unassigned_vehicle, driver_user])
    session.flush()
    driver = Driver(
        organization_id=organization.id,
        user_id=driver_user.id,
        full_name=driver_user.full_name,
        email=driver_user.email,
    )
    session.add(driver)
    session.flush()
    session.add(
        VehicleAssignment(
            organization_id=organization.id,
            vehicle_id=assigned_vehicle.id,
            driver_id=driver.id,
            assigned_by_id=administrator.id,
            started_at=datetime.now(UTC),
        )
    )
    token, session_id, expires_at = create_access_token(driver_user.id)
    session.add(AuthSession(id=session_id, user_id=driver_user.id, expires_at=expires_at))
    session.commit()
    headers = {"Authorization": f"Bearer {token}"}

    allowed_vehicle = client.get(f"/api/v1/vehicles/{assigned_vehicle.id}", headers=headers)
    denied_vehicle = client.get(f"/api/v1/vehicles/{unassigned_vehicle.id}", headers=headers)
    submitted = client.post(
        "/api/v1/fuel-records",
        json={
            "client_record_id": str(uuid4()),
            "vehicle_id": str(assigned_vehicle.id),
            "odometer_reading": 2000,
            "fuel_type": "DIESEL",
            "litres_purchased": "25.000",
            "price_per_litre": "1.2000",
            "currency": "USD",
            "purchased_at": "2026-10-20T12:00:00Z",
        },
        headers=headers,
    )
    denied_submission = client.post(
        "/api/v1/fuel-records",
        json={
            "client_record_id": str(uuid4()),
            "vehicle_id": str(unassigned_vehicle.id),
            "odometer_reading": 2000,
            "fuel_type": "DIESEL",
            "litres_purchased": "25.000",
            "price_per_litre": "1.2000",
            "currency": "USD",
            "purchased_at": "2026-10-20T12:01:00Z",
        },
        headers=headers,
    )

    assert allowed_vehicle.status_code == 200
    assert denied_vehicle.status_code == 404
    assert submitted.status_code == 201
    assert denied_submission.status_code == 403
