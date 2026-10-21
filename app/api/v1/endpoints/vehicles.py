from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession, FleetManager, get_user_organization
from app.models.entities import Driver, Vehicle, VehicleAssignment
from app.schemas.fleet import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate,
    user: FleetManager,
    session: DatabaseSession,
) -> Vehicle:
    organization = get_user_organization(user, session)
    vehicle = Vehicle(organization_id=organization.id, **payload.model_dump())
    session.add(vehicle)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Vehicle identifier already exists") from None
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="vehicle.created",
        resource_type="vehicle",
        resource_id=vehicle.id,
    )
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleResponse])
def list_vehicles(
    user: CurrentUser,
    session: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Vehicle]:
    organization = get_user_organization(user, session)
    statement = select(Vehicle).where(Vehicle.organization_id == organization.id)
    if user.role == "DRIVER":
        driver_id = session.scalar(select(Driver.id).where(Driver.user_id == user.id))
        statement = (
            statement.join(
                VehicleAssignment,
                (VehicleAssignment.vehicle_id == Vehicle.id)
                & (VehicleAssignment.organization_id == organization.id)
                & (VehicleAssignment.ended_at.is_(None)),
            ).where(VehicleAssignment.driver_id == driver_id)
            if driver_id
            else statement.where(False)
        )
    elif user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return list(
        session.scalars(statement.order_by(Vehicle.registration_number).offset(offset).limit(limit))
    )


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: UUID, user: CurrentUser, session: DatabaseSession) -> Vehicle:
    organization = get_user_organization(user, session)
    statement = select(Vehicle).where(
        Vehicle.id == vehicle_id,
        Vehicle.organization_id == organization.id,
    )
    if user.role == "DRIVER":
        driver_id = session.scalar(select(Driver.id).where(Driver.user_id == user.id))
        assignment = (
            session.scalar(
                select(VehicleAssignment.id).where(
                    VehicleAssignment.vehicle_id == vehicle_id,
                    VehicleAssignment.driver_id == driver_id,
                    VehicleAssignment.ended_at.is_(None),
                )
            )
            if driver_id
            else None
        )
        if assignment is None:
            raise HTTPException(status_code=404, detail="Vehicle not found")
    elif user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    vehicle = session.scalar(statement)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    user: FleetManager,
    session: DatabaseSession,
) -> Vehicle:
    organization = get_user_organization(user, session)
    vehicle = session.scalar(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == organization.id,
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one vehicle property must be changed")
    for field, value in changes.items():
        setattr(vehicle, field, value)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Vehicle identifier already exists") from None
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="vehicle.updated",
        resource_type="vehicle",
        resource_id=vehicle.id,
        summary=", ".join(sorted(changes)),
    )
    session.commit()
    session.refresh(vehicle)
    return vehicle
