from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.models.entities import Driver, FuelCorrection, FuelRecord, Vehicle
from app.schemas.fuel import (
    FuelCorrectionCreate,
    FuelCorrectionResponse,
    FuelRecordCreate,
    FuelRecordResponse,
)
from app.services.analytics import validate_datetime_range
from app.services.audit import record_audit
from app.services.fuel import calculated_total, create_fuel_record, ensure_odometer_in_sequence

router = APIRouter(prefix="/fuel-records", tags=["fuel records"])


@router.post("", response_model=FuelRecordResponse, status_code=201)
def submit_fuel_record(
    payload: FuelRecordCreate,
    response: Response,
    user: CurrentUser,
    session: DatabaseSession,
) -> FuelRecord:
    organization = get_user_organization(user, session)
    try:
        record, replayed = create_fuel_record(
            session, user=user, organization=organization, payload=payload
        )
    except IntegrityError:
        session.rollback()
        record, replayed = create_fuel_record(
            session,
            user=user,
            organization=organization,
            payload=payload,
        )
        if not replayed:
            raise HTTPException(
                status_code=503,
                detail="Submission could not be confirmed; retry safely",
            ) from None
    session.commit()
    session.refresh(record)
    if replayed:
        response.status_code = 200
        response.headers["Idempotency-Replayed"] = "true"
    return record


@router.get("", response_model=list[FuelRecordResponse])
def list_fuel_records(
    user: CurrentUser,
    session: DatabaseSession,
    vehicle_id: UUID | None = None,
    driver_id: UUID | None = None,
    purchased_from: datetime | None = None,
    purchased_to: datetime | None = None,
    station_name: str | None = Query(default=None, max_length=160),
    fuel_type: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[FuelRecord]:
    validate_datetime_range(purchased_from, purchased_to)
    organization = get_user_organization(user, session)
    statement = select(FuelRecord).where(FuelRecord.organization_id == organization.id)
    if user.role == "DRIVER":
        statement = statement.where(FuelRecord.submitted_by_id == user.id)
    elif user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    if vehicle_id is not None:
        statement = statement.where(FuelRecord.vehicle_id == vehicle_id)
    if driver_id is not None:
        statement = statement.where(FuelRecord.driver_id == driver_id)
    if purchased_from is not None:
        statement = statement.where(FuelRecord.purchased_at >= purchased_from)
    if purchased_to is not None:
        statement = statement.where(FuelRecord.purchased_at <= purchased_to)
    if station_name is not None:
        statement = statement.where(FuelRecord.station_name.ilike(f"%{station_name}%"))
    if fuel_type is not None:
        statement = statement.where(FuelRecord.fuel_type == fuel_type.upper())
    return list(
        session.scalars(
            statement.order_by(FuelRecord.purchased_at.desc()).offset(offset).limit(limit)
        )
    )


@router.get("/{record_id}", response_model=FuelRecordResponse)
def get_fuel_record(record_id: UUID, user: CurrentUser, session: DatabaseSession) -> FuelRecord:
    organization = get_user_organization(user, session)
    statement = select(FuelRecord).where(
        FuelRecord.id == record_id,
        FuelRecord.organization_id == organization.id,
    )
    if user.role == "DRIVER":
        statement = statement.where(FuelRecord.submitted_by_id == user.id)
    elif user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    record = session.scalar(statement)
    if record is None:
        raise HTTPException(status_code=404, detail="Fuel record not found")
    return record


@router.post("/{record_id}/corrections", status_code=201)
def correct_fuel_record(
    record_id: UUID,
    payload: FuelCorrectionCreate,
    user: CurrentUser,
    session: DatabaseSession,
) -> dict[str, str]:
    if user.role != "ORG_ADMIN":
        raise HTTPException(
            status_code=403, detail="Only organization administrators may correct records"
        )
    organization = get_user_organization(user, session)
    record = session.scalar(
        select(FuelRecord)
        .where(
            FuelRecord.id == record_id,
            FuelRecord.organization_id == organization.id,
        )
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Fuel record not found")
    changes = payload.corrected_values.model_dump(exclude_unset=True)
    new_values = payload.corrected_values.model_dump(exclude_unset=True, mode="json")
    old_values = {key: str(getattr(record, key)) for key in changes}
    vehicle = session.scalar(
        select(Vehicle).where(
            Vehicle.id == record.vehicle_id,
            Vehicle.organization_id == organization.id,
        )
    )
    new_currency = changes.get("currency", record.currency)
    if new_currency != organization.default_currency:
        raise HTTPException(
            status_code=422,
            detail="Currency must match the organization's configured currency",
        )
    new_fuel_type = changes.get("fuel_type", record.fuel_type)
    if vehicle is None or new_fuel_type not in {vehicle.fuel_type, "OTHER"}:
        raise HTTPException(status_code=422, detail="Fuel type does not match the vehicle")
    if "driver_id" in changes and changes["driver_id"] is not None:
        driver_exists = session.scalar(
            select(Driver.id).where(
                Driver.id == changes["driver_id"],
                Driver.organization_id == organization.id,
            )
        )
        if driver_exists is None:
            raise HTTPException(status_code=404, detail="Driver not found")

    corrected_odometer = changes.get("odometer_reading", record.odometer_reading)
    corrected_purchase_time = changes.get("purchased_at", record.purchased_at)
    if "odometer_reading" in changes or "purchased_at" in changes:
        ensure_odometer_in_sequence(
            session,
            organization.id,
            record.vehicle_id,
            corrected_purchase_time,
            corrected_odometer,
            exclude_record_id=record.id,
        )

    total_is_corrected = "litres_purchased" in changes or "price_per_litre" in changes
    if total_is_corrected:
        old_values["total_amount"] = str(record.total_amount)
    for key, value in changes.items():
        setattr(record, key, value.astimezone(UTC) if key == "purchased_at" else value)
    if total_is_corrected:
        record.total_amount = calculated_total(record.litres_purchased, record.price_per_litre)
        new_values["total_amount"] = str(record.total_amount)

    correction = FuelCorrection(
        organization_id=organization.id,
        fuel_record_id=record.id,
        corrected_by_id=user.id,
        reason=payload.reason,
        old_values=old_values,
        new_values=new_values,
    )
    session.add(correction)
    session.flush()
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="fuel_record.corrected",
        resource_type="fuel_record",
        resource_id=record.id,
        summary=payload.reason,
    )
    session.commit()
    return {"correction_id": str(correction.id), "status": "corrected"}


@router.get("/{record_id}/corrections", response_model=list[FuelCorrectionResponse])
def list_fuel_corrections(
    record_id: UUID,
    user: CurrentUser,
    session: DatabaseSession,
) -> list[FuelCorrection]:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    organization = get_user_organization(user, session)
    record_exists = session.scalar(
        select(FuelRecord.id).where(
            FuelRecord.id == record_id,
            FuelRecord.organization_id == organization.id,
        )
    )
    if record_exists is None:
        raise HTTPException(status_code=404, detail="Fuel record not found")
    return list(
        session.scalars(
            select(FuelCorrection)
            .where(
                FuelCorrection.fuel_record_id == record_id,
                FuelCorrection.organization_id == organization.id,
            )
            .order_by(FuelCorrection.created_at.desc())
        )
    )
