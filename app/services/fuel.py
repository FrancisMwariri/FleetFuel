from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import (
    Alert,
    Driver,
    FuelRecord,
    Organization,
    User,
    Vehicle,
    VehicleAssignment,
)
from app.schemas.fuel import FuelRecordCreate
from app.services.audit import record_audit


def calculated_total(litres: Decimal, price_per_litre: Decimal) -> Decimal:
    total = (litres * price_per_litre).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if total > Decimal("9999999999.99"):
        raise HTTPException(
            status_code=422,
            detail="Calculated total exceeds supported currency precision",
        )
    return total


def ensure_odometer_in_sequence(
    session: Session,
    organization_id: UUID,
    vehicle_id: UUID,
    purchased_at: datetime,
    odometer_reading: int,
    exclude_record_id: UUID | None = None,
) -> None:
    preceding_statement = select(FuelRecord.odometer_reading).where(
        FuelRecord.organization_id == organization_id,
        FuelRecord.vehicle_id == vehicle_id,
        FuelRecord.purchased_at <= purchased_at,
    )
    following_statement = select(FuelRecord.odometer_reading).where(
        FuelRecord.organization_id == organization_id,
        FuelRecord.vehicle_id == vehicle_id,
        FuelRecord.purchased_at > purchased_at,
    )
    if exclude_record_id is not None:
        preceding_statement = preceding_statement.where(FuelRecord.id != exclude_record_id)
        following_statement = following_statement.where(FuelRecord.id != exclude_record_id)
    preceding = session.scalar(
        preceding_statement.order_by(
            FuelRecord.purchased_at.desc(), FuelRecord.received_at.desc()
        ).limit(1)
    )
    following = session.scalar(
        following_statement.order_by(FuelRecord.purchased_at, FuelRecord.received_at).limit(1)
    )
    if preceding is not None and odometer_reading < preceding:
        raise HTTPException(
            status_code=422, detail="Odometer reading is below the preceding record"
        )
    if following is not None and odometer_reading > following:
        raise HTTPException(status_code=422, detail="Odometer reading exceeds the following record")


def create_fuel_record(
    session: Session,
    *,
    user: User,
    organization: Organization,
    payload: FuelRecordCreate,
) -> tuple[FuelRecord, bool]:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "DRIVER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    existing = session.scalar(
        select(FuelRecord).where(
            FuelRecord.organization_id == organization.id,
            FuelRecord.client_record_id == payload.client_record_id,
        )
    )
    if existing is not None:
        if user.role == "DRIVER" and existing.submitted_by_id != user.id:
            raise HTTPException(status_code=404, detail="Fuel record not found")
        existing_purchased_at = existing.purchased_at
        if existing_purchased_at.tzinfo is None:
            existing_purchased_at = existing_purchased_at.replace(tzinfo=UTC)
        replay_matches = (
            existing.vehicle_id == payload.vehicle_id
            and existing.odometer_reading == payload.odometer_reading
            and existing.fuel_type == payload.fuel_type
            and existing.litres_purchased == payload.litres_purchased
            and existing.price_per_litre == payload.price_per_litre
            and existing.currency == payload.currency
            and existing.station_name == payload.station_name
            and existing_purchased_at == payload.purchased_at.astimezone(UTC)
            and existing.source == payload.source
            and (payload.driver_id is None or existing.driver_id == payload.driver_id)
        )
        if not replay_matches:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Client record ID was already used for different data",
            )
        return existing, True

    vehicle = session.scalar(
        select(Vehicle).where(
            Vehicle.id == payload.vehicle_id,
            Vehicle.organization_id == organization.id,
            Vehicle.status == "ACTIVE",
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if payload.fuel_type not in {vehicle.fuel_type, "OTHER"}:
        raise HTTPException(status_code=422, detail="Fuel type does not match the vehicle")
    if payload.currency != organization.default_currency:
        raise HTTPException(
            status_code=422, detail="Currency must match the organization's configured currency"
        )

    driver_id = payload.driver_id
    if user.role == "DRIVER":
        driver_id = session.scalar(
            select(Driver.id).where(
                Driver.user_id == user.id,
                Driver.organization_id == organization.id,
                Driver.status == "ACTIVE",
            )
        )
        if driver_id is None:
            raise HTTPException(
                status_code=403, detail="No active driver profile is linked to this account"
            )
        if payload.driver_id is not None and payload.driver_id != driver_id:
            raise HTTPException(
                status_code=403, detail="Driver cannot submit on behalf of another driver"
            )
        assignment_id = session.scalar(
            select(VehicleAssignment.id).where(
                VehicleAssignment.organization_id == organization.id,
                VehicleAssignment.vehicle_id == vehicle.id,
                VehicleAssignment.driver_id == driver_id,
                VehicleAssignment.ended_at.is_(None),
            )
        )
        if assignment_id is None:
            raise HTTPException(status_code=403, detail="Vehicle is not assigned to this driver")
    elif driver_id is not None:
        valid_driver = session.scalar(
            select(Driver.id).where(
                Driver.id == driver_id,
                Driver.organization_id == organization.id,
                Driver.status == "ACTIVE",
            )
        )
        if valid_driver is None:
            raise HTTPException(status_code=404, detail="Driver not found")

    ensure_odometer_in_sequence(
        session, organization.id, vehicle.id, payload.purchased_at, payload.odometer_reading
    )
    record = FuelRecord(
        organization_id=organization.id,
        vehicle_id=vehicle.id,
        driver_id=driver_id,
        submitted_by_id=user.id,
        client_record_id=payload.client_record_id,
        odometer_reading=payload.odometer_reading,
        fuel_type=payload.fuel_type,
        litres_purchased=payload.litres_purchased,
        price_per_litre=payload.price_per_litre,
        total_amount=calculated_total(payload.litres_purchased, payload.price_per_litre),
        currency=payload.currency,
        station_name=payload.station_name,
        purchased_at=payload.purchased_at.astimezone(UTC),
        source=payload.source,
        sync_status="ACCEPTED",
    )
    session.add(record)
    session.flush()
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="fuel_record.accepted",
        resource_type="fuel_record",
        resource_id=record.id,
        summary=f"source={record.source}",
    )
    historical_amounts = list(
        session.scalars(
            select(FuelRecord.total_amount)
            .where(
                FuelRecord.organization_id == organization.id,
                FuelRecord.vehicle_id == vehicle.id,
                FuelRecord.id != record.id,
            )
            .order_by(FuelRecord.purchased_at.desc())
            .limit(20)
        )
    )
    if len(historical_amounts) >= 3:
        baseline = median(historical_amounts)
        multiplier = get_settings().unusual_spend_multiplier
        if baseline > 0 and record.total_amount > baseline * multiplier:
            alert = Alert(
                organization_id=organization.id,
                vehicle_id=vehicle.id,
                rule_code="SPEND_ABOVE_VEHICLE_BASELINE",
                reason=(
                    f"Recorded purchase total {record.total_amount} {record.currency} exceeded "
                    f"{multiplier}x the vehicle's recent median {baseline} {record.currency}. "
                    "This is a review signal, not evidence of fuel consumption or misconduct."
                ),
                severity="MEDIUM",
                related_record_ids=[str(record.id)],
            )
            session.add(alert)
            session.flush()
            record_audit(
                session,
                organization_id=organization.id,
                actor_id=None,
                action="alert.created",
                resource_type="alert",
                resource_id=alert.id,
                summary=alert.rule_code,
            )
    return record, False
