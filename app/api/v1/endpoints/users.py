from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, update

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.models.entities import AuthSession, User
from app.schemas.users import UserAdminResponse, UserAdminUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserAdminResponse])
def list_users(
    user: CurrentUser,
    session: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    organization = get_user_organization(user, session)
    statement = select(User).where(User.organization_id == organization.id)
    if user.role == "DRIVER":
        statement = statement.where(User.id == user.id)
    elif user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return list(session.scalars(statement.order_by(User.email).offset(offset).limit(limit)))


@router.patch("/{user_id}", response_model=UserAdminResponse)
def update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    user: CurrentUser,
    session: DatabaseSession,
) -> User:
    if user.role != "ORG_ADMIN":
        raise HTTPException(status_code=403, detail="Organization administrator role required")
    if user.id == user_id:
        raise HTTPException(status_code=422, detail="Administrators cannot modify their own access")
    organization = get_user_organization(user, session)
    target = session.scalar(
        select(User).where(User.id == user_id, User.organization_id == organization.id)
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is None and payload.is_active is None:
        raise HTTPException(status_code=422, detail="At least one user property must be changed")
    changes: list[str] = []
    if payload.role is not None:
        target.role = payload.role
        changes.append(f"role={payload.role}")
    if payload.is_active is not None:
        target.is_active = payload.is_active
        changes.append(f"is_active={payload.is_active}")
        if not payload.is_active:
            session.execute(
                update(AuthSession)
                .where(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="user.access_changed",
        resource_type="user",
        resource_id=target.id,
        summary=f"{', '.join(changes)}; reason={payload.reason}",
    )
    session.commit()
    session.refresh(target)
    return target
