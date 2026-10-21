from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import AuthSession, Organization, User
from app.schemas.organizations import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    user: CurrentUser,
    session: DatabaseSession,
) -> Organization:
    if user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Platform administrator role required")
    organization = Organization(**payload.model_dump())
    session.add(organization)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Organization slug already exists") from None
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="organization.created",
        resource_type="organization",
        resource_id=organization.id,
    )
    session.commit()
    session.refresh(organization)
    return organization


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: UUID,
    user: CurrentUser,
    session: DatabaseSession,
) -> Organization:
    if user.role == "SUPER_ADMIN":
        organization = session.get(Organization, organization_id)
    elif user.organization_id is not None and user.organization_id == organization_id:
        organization = session.scalar(
            select(Organization).where(Organization.id == user.organization_id)
        )
    else:
        organization = None
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    user: CurrentUser,
    session: DatabaseSession,
) -> Organization:
    if user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Platform administrator role required")
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    organization.status = payload.status
    if payload.status == "SUSPENDED":
        session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id.in_(
                    select(User.id).where(User.organization_id == organization.id)
                ),
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="organization.status_changed",
        resource_type="organization",
        resource_id=organization.id,
        summary=f"status={payload.status}; reason={payload.reason}",
    )
    session.commit()
    session.refresh(organization)
    return organization
