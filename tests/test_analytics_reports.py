from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Alert, AuditEvent, Organization, User, Vehicle


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
        registration_number="ANL-100",
        fuel_type="DIESEL",
    )
    session.add(vehicle)
    session.commit()
    return vehicle


def submit_record(
    client: TestClient,
    token: str,
    vehicle_id: str,
    *,
    index: int,
    litres: str = "20.000",
    station: str = "Fleet Station",
) -> None:
    response = client.post(
        "/api/v1/fuel-records",
        json={
            "client_record_id": str(uuid4()),
            "vehicle_id": vehicle_id,
            "odometer_reading": 1000 * index,
            "fuel_type": "DIESEL",
            "litres_purchased": litres,
            "price_per_litre": "1.0000",
            "currency": "USD",
            "station_name": station,
            "purchased_at": f"2026-10-{index + 1:02d}T10:00:00Z",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_dashboard_distance_and_vehicle_history_alert(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, _ = api_client
    vehicle = add_vehicle(session, organization)
    token = login(client)
    for index in range(1, 4):
        submit_record(client, token, str(vehicle.id), index=index)
    submit_record(client, token, str(vehicle.id), index=4, litres="100.000")

    dashboard = client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token}"}
    )
    alerts = client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token}"})

    assert dashboard.status_code == 200
    assert dashboard.json()["purchase_count"] == 4
    assert dashboard.json()["distance_between_recorded_odometer_readings"] == 3000
    assert dashboard.json()["valid_odometer_intervals"] == 3
    assert dashboard.json()["purchase_amount_per_litre_is_not_fuel_consumption"] is True
    assert len(alerts.json()) == 1
    assert alerts.json()[0]["rule_code"] == "SPEND_ABOVE_VEHICLE_BASELINE"
    assert "not evidence" in alerts.json()[0]["reason"]

    alert_id = alerts.json()[0]["id"]
    resolution = client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={"status": "RESOLVED", "resolution_notes": "Reviewed supporting records"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resolution.status_code == 200
    assert resolution.json()["status"] == "RESOLVED"
    assert session.scalar(select(Alert).where(Alert.id == UUID(alert_id))).resolution_notes


def test_csv_export_neutralizes_formula_and_is_audited(
    api_client: tuple[TestClient, Session, Organization, User],
) -> None:
    client, session, organization, user = api_client
    vehicle = add_vehicle(session, organization)
    token = login(client)
    submit_record(
        client,
        token,
        str(vehicle.id),
        index=1,
        station='=HYPERLINK("https://invalid.example")',
    )

    response = client.get(
        "/api/v1/reports/fuel-records.csv", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "'=HYPERLINK" in response.text
    assert (
        session.scalar(
            select(AuditEvent.id).where(
                AuditEvent.actor_id == user.id,
                AuditEvent.action == "report.exported",
                AuditEvent.organization_id == organization.id,
            )
        )
        is not None
    )
