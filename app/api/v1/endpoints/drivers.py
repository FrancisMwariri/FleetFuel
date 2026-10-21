from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, FleetManager, get_user_organization
from app.models.entities import Driver
from app.schemas.fleet import DriverCreate, DriverResponse, DriverUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreate,
    user: FleetManager,
    session: DatabaseSession,
) -> Driver:
    organization = get_user_organization(user, session)
    driver = Driver(organization_id=organization.id, **payload.model_dump())
    session.add(driver)
    session.flush()
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="driver.created",
        resource_type="driver",
        resource_id=driver.id,
    )
    session.commit()
    session.refresh(driver)
    return driver


@router.get("", response_model=list[DriverResponse])
def list_drivers(
    user: CurrentUser,
    session: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Driver]:
    organization = get_user_organization(user, session)
    statement = select(Driver).where(Driver.organization_id == organization.id)
    if user.role == "DRIVER":
        statement = statement.where(Driver.user_id == user.id)
    elif user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return list(session.scalars(statement.order_by(Driver.full_name).offset(offset).limit(limit)))


@router.patch("/{driver_id}", response_model=DriverResponse)
def update_driver(
    driver_id: UUID,
    payload: DriverUpdate,
    user: FleetManager,
    session: DatabaseSession,
) -> Driver:
    organization = get_user_organization(user, session)
    driver = session.scalar(
        select(Driver).where(
            Driver.id == driver_id,
            Driver.organization_id == organization.id,
        )
    )
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one driver property must be changed")
    for field, value in changes.items():
        setattr(driver, field, value)
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="driver.updated",
        resource_type="driver",
        resource_id=driver.id,
        summary=", ".join(sorted(changes)),
    )
    session.commit()
    session.refresh(driver)
    return driver
