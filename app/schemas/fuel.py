from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FuelType = Literal["DIESEL", "PETROL", "GASOLINE", "ELECTRIC", "OTHER"]


class FuelRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_record_id: UUID
    vehicle_id: UUID
    driver_id: UUID | None = None
    odometer_reading: int = Field(ge=0)
    fuel_type: FuelType
    litres_purchased: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    price_per_litre: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)
    station_name: str | None = Field(default=None, max_length=160)
    purchased_at: datetime
    source: Literal["ONLINE", "OFFLINE"] = "ONLINE"

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_timezone(self) -> "FuelRecordCreate":
        if self.purchased_at.tzinfo is None or self.purchased_at.utcoffset() is None:
            raise ValueError("purchased_at must include a timezone")
        return self


class FuelRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_record_id: UUID
    vehicle_id: UUID
    driver_id: UUID | None
    submitted_by_id: UUID
    odometer_reading: int
    fuel_type: str
    litres_purchased: Decimal
    price_per_litre: Decimal
    total_amount: Decimal
    currency: str
    station_name: str | None
    purchased_at: datetime
    received_at: datetime
    source: str
    sync_status: str


class FuelCorrectionChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    odometer_reading: int | None = Field(default=None, ge=0)
    fuel_type: FuelType | None = None
    litres_purchased: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    price_per_litre: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    station_name: str | None = Field(default=None, max_length=160)
    purchased_at: datetime | None = None
    driver_id: UUID | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_change_set(self) -> "FuelCorrectionChanges":
        if not self.model_fields_set:
            raise ValueError("At least one corrected value is required")
        required_fields = {
            "odometer_reading",
            "fuel_type",
            "litres_purchased",
            "price_per_litre",
            "currency",
            "purchased_at",
        }
        if any(getattr(self, field) is None for field in self.model_fields_set & required_fields):
            raise ValueError("Corrected values cannot be null for required fields")
        if self.purchased_at is not None and self.purchased_at.utcoffset() is None:
            raise ValueError("purchased_at must include a timezone")
        return self


class FuelCorrectionCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    corrected_values: FuelCorrectionChanges


class FuelCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fuel_record_id: UUID
    corrected_by_id: UUID
    reason: str
    old_values: dict[str, object]
    new_values: dict[str, object]
    created_at: datetime
