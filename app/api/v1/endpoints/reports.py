import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.services.analytics import fuel_records_for_period, validate_datetime_range
from app.services.audit import record_audit

router = APIRouter(prefix="/reports", tags=["reports"])


def spreadsheet_safe(value: object) -> str:
    text = str(value) if value is not None else ""
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


@router.get("/fuel-records.csv")
def export_fuel_records(
    user: CurrentUser,
    session: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
    vehicle_id: UUID | None = None,
    driver_id: UUID | None = None,
    limit: int = Query(default=5000, ge=1, le=10000),
) -> StreamingResponse:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    validate_datetime_range(start, end)
    organization = get_user_organization(user, session)
    records = fuel_records_for_period(
        session,
        organization_id=organization.id,
        start=start,
        end=end,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        limit=limit,
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "record_id",
            "vehicle_id",
            "driver_id",
            "odometer_reading",
            "fuel_type",
            "litres_purchased",
            "price_per_litre",
            "total_amount",
            "currency",
            "station_name",
            "purchased_at_utc",
            "received_at_utc",
            "source",
        ]
    )
    for record in records:
        writer.writerow(
            [
                str(record.id),
                str(record.vehicle_id),
                str(record.driver_id) if record.driver_id else "",
                record.odometer_reading,
                record.fuel_type,
                record.litres_purchased,
                record.price_per_litre,
                record.total_amount,
                record.currency,
                spreadsheet_safe(record.station_name),
                record.purchased_at.isoformat(),
                record.received_at.isoformat(),
                record.source,
            ]
        )
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="report.exported",
        resource_type="fuel_records",
        resource_id=None,
        summary=f"count={len(records)}",
    )
    session.commit()
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=fleetfuel-records.csv"},
    )
