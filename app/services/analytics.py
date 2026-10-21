from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import FuelRecord


def validate_datetime_range(start: datetime | None, end: datetime | None) -> None:
    if any(value is not None and value.utcoffset() is None for value in (start, end)):
        raise HTTPException(status_code=422, detail="Date filters must include a timezone")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")


def fuel_records_for_period(
    session: Session,
    *,
    organization_id: UUID,
    start: datetime | None,
    end: datetime | None,
    vehicle_id: UUID | None = None,
    driver_id: UUID | None = None,
    limit: int = 10_000,
) -> list[FuelRecord]:
    statement = select(FuelRecord).where(FuelRecord.organization_id == organization_id)
    if start is not None:
        statement = statement.where(FuelRecord.purchased_at >= start)
    if end is not None:
        statement = statement.where(FuelRecord.purchased_at <= end)
    if vehicle_id is not None:
        statement = statement.where(FuelRecord.vehicle_id == vehicle_id)
    if driver_id is not None:
        statement = statement.where(FuelRecord.driver_id == driver_id)
    return list(
        session.scalars(
            statement.order_by(
                FuelRecord.vehicle_id,
                FuelRecord.purchased_at,
                FuelRecord.id,
            ).limit(limit)
        )
    )


def summarize_fuel_records(records: list[FuelRecord]) -> dict[str, object]:
    total_amount = sum((record.total_amount for record in records), Decimal("0.00"))
    total_litres = sum((record.litres_purchased for record in records), Decimal("0.000"))
    distances: list[int] = []
    previous_by_vehicle: dict[UUID, FuelRecord] = {}
    for record in records:
        previous = previous_by_vehicle.get(record.vehicle_id)
        if previous is not None and record.odometer_reading >= previous.odometer_reading:
            distances.append(record.odometer_reading - previous.odometer_reading)
        previous_by_vehicle[record.vehicle_id] = record
    return {
        "purchase_count": len(records),
        "total_amount": total_amount,
        "total_litres_purchased": total_litres,
        "currency": records[0].currency if records else None,
        "distance_between_recorded_odometer_readings": sum(distances),
        "valid_odometer_intervals": len(distances),
        "purchase_amount_per_litre_is_not_fuel_consumption": True,
    }
