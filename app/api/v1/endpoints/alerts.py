from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.models.entities import Alert
from app.schemas.analytics import AlertResponse, AlertUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    user: CurrentUser,
    session: DatabaseSession,
    alert_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Alert]:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "VIEWER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    organization = get_user_organization(user, session)
    statement = select(Alert).where(Alert.organization_id == organization.id)
    if alert_status:
        statement = statement.where(Alert.status == alert_status.upper())
    return list(
        session.scalars(statement.order_by(Alert.detected_at.desc()).offset(offset).limit(limit))
    )


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    user: CurrentUser,
    session: DatabaseSession,
) -> Alert:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    if payload.status in {"RESOLVED", "DISMISSED"} and not payload.resolution_notes:
        raise HTTPException(status_code=422, detail="Resolution notes are required")
    organization = get_user_organization(user, session)
    alert = session.scalar(
        select(Alert).where(Alert.id == alert_id, Alert.organization_id == organization.id)
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = payload.status
    alert.assigned_reviewer_id = user.id
    alert.resolution_notes = payload.resolution_notes
    record_audit(
        session,
        organization_id=organization.id,
        actor_id=user.id,
        action="alert.status_changed",
        resource_type="alert",
        resource_id=alert.id,
        summary=f"status={alert.status}",
    )
    session.commit()
    session.refresh(alert)
    return alert
