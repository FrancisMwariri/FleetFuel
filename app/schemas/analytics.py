from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertUpdate(BaseModel):
    status: str = Field(pattern="^(UNDER_REVIEW|RESOLVED|DISMISSED)$")
    resolution_notes: str | None = Field(default=None, max_length=1000)


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    rule_code: str
    reason: str
    severity: str
    status: str
    related_record_ids: list[str]
    assigned_reviewer_id: UUID | None
    resolution_notes: str | None
    detected_at: datetime
    updated_at: datetime


class DashboardResponse(BaseModel):
    vehicle_count: int
    active_vehicle_count: int
    open_alert_count: int
    recent_fuel_record_ids: list[UUID]
    purchase_count: int
    total_amount: str
    total_litres_purchased: str
    currency: str | None
    distance_between_recorded_odometer_readings: int
    valid_odometer_intervals: int
    purchase_amount_per_litre_is_not_fuel_consumption: bool
    summary_truncated: bool
