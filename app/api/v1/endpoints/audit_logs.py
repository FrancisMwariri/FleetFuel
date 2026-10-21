from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.models.entities import AuditEvent
from app.schemas.audit import AuditEventResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    user: CurrentUser,
    session: DatabaseSession,
    resource_type: str | None = Query(default=None, max_length=80),
    resource_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEvent]:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    organization = get_user_organization(user, session)
    statement = select(AuditEvent).where(AuditEvent.organization_id == organization.id)
    if resource_type:
        statement = statement.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        statement = statement.where(AuditEvent.resource_id == str(resource_id))
    return list(
        session.scalars(
            statement.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
        )
    )
