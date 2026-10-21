from uuid import UUID

from sqlalchemy.orm import Session

from app.core.request_context import request_id_context
from app.models.entities import AuditEvent


def record_audit(
    session: Session,
    *,
    organization_id: UUID | None,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None,
    summary: str | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            request_id=request_id_context.get(),
            summary=summary,
        )
    )
