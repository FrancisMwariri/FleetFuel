from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.models.entities import Alert, FuelRecord, Vehicle
from app.schemas.analytics import DashboardResponse
from app.services.analytics import fuel_records_for_period, summarize_fuel_records

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardResponse)
def dashboard_summary(user: CurrentUser, session: DatabaseSession) -> DashboardResponse:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    organization = get_user_organization(user, session)
    records = fuel_records_for_period(
        session,
        organization_id=organization.id,
        start=None,
        end=None,
        limit=10_000,
    )
    summary = summarize_fuel_records(records)
    recent_records = list(
        session.scalars(
            select(FuelRecord.id)
            .where(FuelRecord.organization_id == organization.id)
            .order_by(FuelRecord.purchased_at.desc())
            .limit(10)
        )
    )
    return DashboardResponse(
        vehicle_count=session.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.organization_id == organization.id)
        )
        or 0,
        active_vehicle_count=session.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(
                Vehicle.organization_id == organization.id,
                Vehicle.status == "ACTIVE",
            )
        )
        or 0,
        open_alert_count=session.scalar(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.organization_id == organization.id,
                Alert.status.in_(["OPEN", "UNDER_REVIEW"]),
            )
        )
        or 0,
        recent_fuel_record_ids=recent_records,
        purchase_count=summary["purchase_count"],
        total_amount=str(summary["total_amount"]),
        total_litres_purchased=str(summary["total_litres_purchased"]),
        currency=summary["currency"],
        distance_between_recorded_odometer_readings=summary[
            "distance_between_recorded_odometer_readings"
        ],
        valid_odometer_intervals=summary["valid_odometer_intervals"],
        purchase_amount_per_litre_is_not_fuel_consumption=True,
        summary_truncated=len(records) == 10_000,
    )
