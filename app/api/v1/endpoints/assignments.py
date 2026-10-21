from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import DatabaseSession, FleetManager, get_user_organization
from app.models.entities import Driver, Vehicle, VehicleAssignment
from app.schemas.fleet import AssignmentCreate, AssignmentResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    user: FleetManager,
    session: DatabaseSession,
) -> VehicleAssignment:
    organization = get_user_organization(user, session)
    vehicle = session.scalar(
        select(Vehicle).where(
            Vehicle.id == payload.vehicle_id,
            Vehicle.organization_id == organization.id,
            Vehicle.status == "ACTIVE",
        )
    )
    driver = session.scalar(
        select(Driver).where(
            Driver.id == payload.driver_id,
            Driver.organization_id == organization.id,
            Driver.status == "ACTIVE",
        )
    )
    if vehicle is None or driver is None:
        raise HTTPException(status_code=404, detail="Vehicle or driver not found")
    conflict = session.scalar(
        select(VehicleAssignment.id).where(
            VehicleAssignment.ended_at.is_(None),
            (VehicleAssignment.vehicle_id == vehicle.id)
            | (VehicleAssignment.driver_id == driver.id),
        )
    )
    if conflict is not None:
        raise HTTPException(
            status_code=409, detail="Vehicle or driver already has an active assignment"
        )
    assignment = VehicleAssignment(
        organization_id=organization.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        assigned_by_id=user.id,
        started_at=payload.started_at or datetime.now(UTC),
    )
    session.add(assignment)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Vehicle or driver already has an active assignment",
        ) from None
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="assignment.created",
        resource_type="vehicle_assignment",
        resource_id=assignment.id,
    )
    session.commit()
    session.refresh(assignment)
    return assignment


@router.post("/{assignment_id}/end", response_model=AssignmentResponse)
def end_assignment(
    assignment_id: UUID,
    user: FleetManager,
    session: DatabaseSession,
) -> VehicleAssignment:
    organization = get_user_organization(user, session)
    assignment = session.scalar(
        select(VehicleAssignment).where(
            VehicleAssignment.id == assignment_id,
            VehicleAssignment.organization_id == organization.id,
            VehicleAssignment.ended_at.is_(None),
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Active assignment not found")
    assignment.ended_at = datetime.now(UTC)
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="assignment.ended",
        resource_type="vehicle_assignment",
        resource_id=assignment.id,
    )
    session.commit()
    session.refresh(assignment)
    return assignment
