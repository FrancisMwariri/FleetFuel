from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Attachment, FuelRecord, Organization, User, Vehicle


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def add_vehicle(session: Session, organization: Organization) -> Vehicle:
    vehicle = Vehicle(
        organization_id=organization.id,
        registration_number="SYNC-100",
        fuel_type="DIESEL",
    )
    session.add(vehicle)
    session.commit()
    return vehicle


def sync_record(vehicle_id: str) -> dict[str, object]:
    return {
        "client_record_id": str(uuid4()),
        "vehicle_id": vehicle_id,
        "odometer_reading": 4500,
        "fuel_type": "DIESEL",
        "litres_purchased": "20.000",
        "price_per_litre": "1.5000",
        "currency": "USD",
        "purchased_at": "2026-10-20T11:00:00Z",
    }


def test_sync_batch_returns_per_record_results(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization)
    token = login(client)
    valid_record = sync_record(str(vehicle.id))

    response = client.post(
        "/api/v1/sync/fuel-records",
        json=[valid_record, {"client_record_id": "not-a-uuid"}, "not-an-object"],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["status"] for item in results] == [
        "accepted",
        "rejected_validation",
        "rejected_validation",
    ]
    stored = list(session.scalars(select(FuelRecord)))
    assert len(stored) == 1
    assert stored[0].source == "OFFLINE"


def test_attachment_requires_valid_image_signature(
    api_client: tuple[TestClient, Session, Organization, User],
    monkeypatch: object,
    tmp_path: object,
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization)
    token = login(client)
    record_payload = sync_record(str(vehicle.id))
    record = client.post(
        "/api/v1/fuel-records",
        json=record_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert record.status_code == 201
    monkeypatch.setenv("FLEETFUEL_ATTACHMENT_DIRECTORY", str(tmp_path))  # type: ignore[attr-defined]
    get_settings.cache_clear()

    response = client.post(
        f"/api/v1/fuel-records/{record.json()['id']}/attachments?kind=RECEIPT",
        files={"upload": ("receipt.png", b"not an image", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 415


def test_valid_attachment_retry_is_idempotent(
    api_client: tuple[TestClient, Session, Organization, User],
    monkeypatch,
    tmp_path,
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization)
    token = login(client)
    record = client.post(
        "/api/v1/fuel-records",
        json=sync_record(str(vehicle.id)),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert record.status_code == 201
    monkeypatch.setenv("FLEETFUEL_ATTACHMENT_DIRECTORY", str(tmp_path))
    get_settings.cache_clear()
    image_data = BytesIO()
    Image.new("RGB", (8, 8), color="red").save(image_data, format="PNG")
    upload = {
        "upload": ("receipt.png", image_data.getvalue(), "image/png"),
    }
    url = f"/api/v1/fuel-records/{record.json()['id']}/attachments?kind=RECEIPT"
    headers = {"Authorization": f"Bearer {token}"}

    accepted = client.post(url, files=upload, headers=headers)
    replay = client.post(url, files=upload, headers=headers)

    assert accepted.status_code == 201
    assert replay.status_code == 200
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert len(list(session.scalars(select(Attachment.id)))) == 1
    listed = client.get(
        f"/api/v1/fuel-records/{record.json()['id']}/attachments",
        headers=headers,
    )
    assert listed.status_code == 200
    metadata = listed.json()
    assert len(metadata) == 1
    assert metadata[0]["id"] == accepted.json()["id"]
    assert metadata[0]["kind"] == "RECEIPT"
    assert metadata[0]["content_type"] == "image/png"
    assert metadata[0]["size_bytes"] == len(image_data.getvalue())
    assert isinstance(metadata[0]["created_at"], str)
