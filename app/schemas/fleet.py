from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class VehicleCreate(BaseModel):
    registration_number: str = Field(min_length=2, max_length=32)
    fleet_identifier: str | None = Field(default=None, min_length=1, max_length=64)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    manufacturing_year: int | None = Field(default=None, ge=1886, le=2200)
    fuel_type: str = Field(min_length=2, max_length=24)
    tank_capacity_litres: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=3
    )

    @field_validator("registration_number", "fleet_identifier", "fuel_type", mode="before")
    @classmethod
    def normalize_identifiers(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    registration_number: str
    fleet_identifier: str | None
    make: str | None
    model: str | None
    manufacturing_year: int | None
    fuel_type: str
    tank_capacity_litres: Decimal | None
    status: str
    created_at: datetime


class VehicleUpdate(BaseModel):
    registration_number: str | None = Field(default=None, min_length=2, max_length=32)
    fleet_identifier: str | None = Field(default=None, min_length=1, max_length=64)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    manufacturing_year: int | None = Field(default=None, ge=1886, le=2200)
    fuel_type: str | None = Field(default=None, min_length=2, max_length=24)
    tank_capacity_litres: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=3
    )
    status: str | None = Field(default=None, pattern="^(ACTIVE|MAINTENANCE|INACTIVE)$")

    @field_validator("registration_number", "fleet_identifier", "fuel_type", mode="before")
    @classmethod
    def normalize_identifiers(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "VehicleUpdate":
        for field in {"registration_number", "fuel_type", "status"} & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class DriverCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


class DriverUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "DriverUpdate":
        for field in {"full_name", "status"} & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    status: str
    created_at: datetime


class AssignmentCreate(BaseModel):
    vehicle_id: UUID
    driver_id: UUID
    started_at: datetime | None = None

    @model_validator(mode="after")
    def start_must_be_timezone_aware(self) -> "AssignmentCreate":
        if self.started_at is not None and self.started_at.utcoffset() is None:
            raise ValueError("started_at must include a timezone")
        return self


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    driver_id: UUID
    started_at: datetime
    ended_at: datetime | None
