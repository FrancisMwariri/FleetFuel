from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.services.analytics import (
    fuel_records_for_period,
    summarize_fuel_records,
    validate_datetime_range,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(
    user: CurrentUser,
    session: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
    vehicle_id: UUID | None = None,
    driver_id: UUID | None = None,
    limit: int = Query(default=10_000, ge=1, le=10_000),
) -> dict[str, object]:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
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
    summary = summarize_fuel_records(records)
    summary["average_purchase_amount"] = (
        summary["total_amount"] / summary["purchase_count"] if summary["purchase_count"] else None
    )
    summary["summary_truncated"] = len(records) == limit
    return summary
