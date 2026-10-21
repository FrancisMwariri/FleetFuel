import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.core.security import hash_password
from app.models.entities import Driver, Organization, OrganizationInvitation, User
from app.schemas.organizations import (
    InvitationCreate,
    InvitationResponse,
    RegistrationRequest,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/organizations/invitations", tags=["invitations"])


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    user: CurrentUser,
    session: DatabaseSession,
    organization_id: UUID | None = Query(default=None),
) -> InvitationResponse:
    if user.role == "SUPER_ADMIN":
        if organization_id is None:
            raise HTTPException(status_code=422, detail="organization_id is required")
        organization = session.scalar(
            select(Organization).where(
                Organization.id == organization_id,
                Organization.status == "ACTIVE",
            )
        )
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found")
    elif user.role == "ORG_ADMIN":
        organization = get_user_organization(user, session)
        if organization_id is not None and organization_id != organization.id:
            raise HTTPException(status_code=404, detail="Organization not found")
    else:
        raise HTTPException(status_code=403, detail="Organization administrator role required")
    email = str(payload.email).lower()
    if session.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(hours=48)
    invitation = OrganizationInvitation(
        organization_id=organization.id,
        invited_by_id=user.id,
        email=email,
        role=payload.role,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=expires_at,
    )
    session.add(invitation)
    session.flush()
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="invitation.created",
        resource_type="organization_invitation",
        resource_id=invitation.id,
        summary=f"role={payload.role}",
    )
    session.commit()
    return InvitationResponse(invitation_token=raw_token, expires_at=expires_at.isoformat())


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_from_invitation(
    payload: RegistrationRequest,
    session: DatabaseSession,
) -> dict[str, str]:
    token_hash = hashlib.sha256(payload.invitation_token.encode()).hexdigest()
    invitation = session.scalar(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.token_hash == token_hash)
        .with_for_update()
    )
    if invitation is None or invitation.used_at is not None:
        raise HTTPException(status_code=400, detail="Invitation is invalid or already used")
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Invitation has expired")
    if session.scalar(select(User.id).where(User.email == invitation.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        organization_id=invitation.organization_id,
        email=invitation.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=invitation.role,
    )
    invitation.used_at = datetime.now(UTC)
    session.add(user)
    session.flush()
    if user.role == "DRIVER":
        session.add(
            Driver(
                organization_id=invitation.organization_id,
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
            )
        )
    record_audit(
        session,
        organization_id=invitation.organization_id,
        actor_id=user.id,
        action="user.registered_by_invitation",
        resource_type="user",
        resource_id=user.id,
    )
    session.commit()
    return {"user_id": str(user.id), "status": "registered"}
