from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import FuelRecord, Organization, User, Vehicle


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def request_payload(vehicle_id: str, client_record_id: str | None = None) -> dict[str, object]:
    return {
        "client_record_id": client_record_id or str(uuid4()),
        "vehicle_id": vehicle_id,
        "odometer_reading": 128450,
        "fuel_type": "DIESEL",
        "litres_purchased": "30.125",
        "price_per_litre": "1.2345",
        "currency": "USD",
        "station_name": "Depot Fuel",
        "purchased_at": "2026-10-20T10:30:00Z",
        "source": "OFFLINE",
    }


def add_vehicle(session: Session, organization: Organization, registration: str) -> Vehicle:
    vehicle = Vehicle(
        organization_id=organization.id,
        registration_number=registration,
        fuel_type="DIESEL",
    )
    session.add(vehicle)
    session.commit()
    return vehicle


def test_fuel_record_uses_server_calculated_total(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization, "TRK-100")
    token = login(client)

    response = client.post(
        "/api/v1/fuel-records",
        json=request_payload(str(vehicle.id)),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["total_amount"] == "37.19"
    assert response.json()["sync_status"] == "ACCEPTED"


def test_fuel_record_retry_is_idempotent(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization, "TRK-101")
    token = login(client)
    payload = request_payload(str(vehicle.id))
    headers = {"Authorization": f"Bearer {token}"}

    accepted = client.post("/api/v1/fuel-records", json=payload, headers=headers)
    replay = client.post("/api/v1/fuel-records", json=payload, headers=headers)

    assert accepted.status_code == 201
    assert replay.status_code == 200
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert session.scalar(select(FuelRecord.id)) is not None
    assert len(list(session.scalars(select(FuelRecord.id)))) == 1


def test_client_id_cannot_be_reused_for_changed_data(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization, "TRK-102")
    token = login(client)
    payload = request_payload(str(vehicle.id))
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post("/api/v1/fuel-records", json=payload, headers=headers)
    changed_payload = {**payload, "odometer_reading": 128451}

    second = client.post("/api/v1/fuel-records", json=changed_payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_admin_correction_recalculates_and_preserves_history(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization, "TRK-103")
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/fuel-records",
        json=request_payload(str(vehicle.id)),
        headers=headers,
    )
    record_id = created.json()["id"]

    corrected = client.post(
        f"/api/v1/fuel-records/{record_id}/corrections",
        json={
            "reason": "Receipt review corrected the quantity",
            "corrected_values": {"litres_purchased": "31.000"},
        },
        headers=headers,
    )
    record_after = client.get(f"/api/v1/fuel-records/{record_id}", headers=headers)
    corrections = client.get(f"/api/v1/fuel-records/{record_id}/corrections", headers=headers)

    assert corrected.status_code == 201
    assert record_after.json()["id"] == record_id
    assert record_after.json()["total_amount"] == "38.27"
    assert corrections.status_code == 200
    assert corrections.json()[0]["old_values"]["total_amount"] == "37.19"
    assert corrections.json()[0]["new_values"]["total_amount"] == "38.27"


def test_viewer_cannot_submit_fuel_records(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, user = api_client
    vehicle = add_vehicle(session, organization, "TRK-104")
    user.role = "VIEWER"
    session.commit()
    token = login(client)

    response = client.post(
        "/api/v1/fuel-records",
        json=request_payload(str(vehicle.id)),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
