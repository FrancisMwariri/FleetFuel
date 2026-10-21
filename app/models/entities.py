from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_users_org_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthenticationAttempt(Base):
    __tablename__ = "authentication_attempts"
    __table_args__ = (Index("ix_auth_attempt_key_time", "key_hash", "attempted_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invited_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_drivers_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_drivers_user_same_org",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, unique=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_vehicles_org_id"),
        UniqueConstraint("organization_id", "registration_number", name="uq_vehicle_registration"),
        UniqueConstraint("organization_id", "fleet_identifier", name="uq_vehicle_fleet_identifier"),
        CheckConstraint("tank_capacity_litres IS NULL OR tank_capacity_litres > 0"),
        CheckConstraint("manufacturing_year IS NULL OR manufacturing_year BETWEEN 1886 AND 2200"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    registration_number: Mapped[str] = mapped_column(String(32), nullable=False)
    fleet_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    make: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    manufacturing_year: Mapped[int | None] = mapped_column(nullable=True)
    fuel_type: Mapped[str] = mapped_column(String(24), nullable=False)
    tank_capacity_litres: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VehicleAssignment(Base):
    __tablename__ = "vehicle_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "vehicle_id"],
            ["vehicles.organization_id", "vehicles.id"],
            name="fk_assignments_vehicle_same_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "driver_id"],
            ["drivers.organization_id", "drivers.id"],
            name="fk_assignments_driver_same_org",
            ondelete="CASCADE",
        ),
        Index(
            "uq_active_vehicle_assignment",
            "vehicle_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
        Index(
            "uq_active_driver_assignment",
            "driver_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    vehicle_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    driver_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    assigned_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FuelRecord(Base):
    __tablename__ = "fuel_records"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_fuel_records_org_id"),
        UniqueConstraint("organization_id", "client_record_id", name="uq_fuel_client_record"),
        ForeignKeyConstraint(
            ["organization_id", "vehicle_id"],
            ["vehicles.organization_id", "vehicles.id"],
            name="fk_fuel_vehicle_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "driver_id"],
            ["drivers.organization_id", "drivers.id"],
            name="fk_fuel_driver_same_org",
        ),
        CheckConstraint("litres_purchased > 0"),
        CheckConstraint("price_per_litre >= 0"),
        CheckConstraint("total_amount >= 0"),
        CheckConstraint("odometer_reading >= 0"),
        Index("ix_fuel_vehicle_purchase", "organization_id", "vehicle_id", "purchased_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    driver_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    submitted_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    client_record_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    odometer_reading: Mapped[int] = mapped_column(nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(24), nullable=False)
    litres_purchased: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    price_per_litre: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    station_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ONLINE")
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACCEPTED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FuelCorrection(Base):
    __tablename__ = "fuel_corrections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "fuel_record_id"],
            ["fuel_records.organization_id", "fuel_records.id"],
            name="fk_corrections_fuel_same_org",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fuel_record_id: Mapped[UUID] = mapped_column(ForeignKey("fuel_records.id"), nullable=False)
    corrected_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    old_values: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    new_values: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint(
            "fuel_record_id",
            "kind",
            "sha256",
            name="uq_attachment_record_content",
        ),
        ForeignKeyConstraint(
            ["organization_id", "fuel_record_id"],
            ["fuel_records.organization_id", "fuel_records.id"],
            name="fk_attachments_fuel_same_org",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fuel_record_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "vehicle_id"],
            ["vehicles.organization_id", "vehicles.id"],
            name="fk_alerts_vehicle_same_org",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(60), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    related_record_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assigned_reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
