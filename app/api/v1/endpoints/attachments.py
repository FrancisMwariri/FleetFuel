import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.core.config import get_settings
from app.models.entities import Attachment, FuelRecord
from app.services.storage import resolve_storage_key, store_image

router = APIRouter(prefix="/fuel-records/{record_id}/attachments", tags=["attachments"])


@router.get("")
def list_attachments(
    record_id: UUID,
    user: CurrentUser,
    session: DatabaseSession,
) -> list[dict[str, object]]:
    organization = get_user_organization(user, session)
    record = session.scalar(
        select(FuelRecord).where(
            FuelRecord.id == record_id,
            FuelRecord.organization_id == organization.id,
        )
    )
    if record is None or (user.role == "DRIVER" and record.submitted_by_id != user.id):
        raise HTTPException(status_code=404, detail="Fuel record not found")
    attachments = session.scalars(
        select(Attachment)
        .where(
            Attachment.organization_id == organization.id,
            Attachment.fuel_record_id == record.id,
        )
        .order_by(Attachment.created_at)
    )
    return [
        {
            "id": str(attachment.id),
            "kind": attachment.kind,
            "content_type": attachment.content_type,
            "size_bytes": attachment.size_bytes,
            "created_at": attachment.created_at.isoformat(),
        }
        for attachment in attachments
    ]


@router.post("", status_code=201)
async def upload_attachment(
    record_id: UUID,
    kind: str,
    user: CurrentUser,
    session: DatabaseSession,
    response: Response,
    upload: Annotated[UploadFile, File()],
) -> dict[str, object]:
    if user.role not in {"ORG_ADMIN", "FLEET_MANAGER", "DRIVER"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    if kind not in {"RECEIPT", "ODOMETER"}:
        raise HTTPException(status_code=422, detail="Attachment kind must be RECEIPT or ODOMETER")
    organization = get_user_organization(user, session)
    record = session.scalar(
        select(FuelRecord).where(
            FuelRecord.id == record_id,
            FuelRecord.organization_id == organization.id,
        )
    )
    if record is None or (user.role == "DRIVER" and record.submitted_by_id != user.id):
        raise HTTPException(status_code=404, detail="Fuel record not found")
    settings = get_settings()
    content = await upload.read(settings.max_attachment_bytes + 1)
    if len(content) > settings.max_attachment_bytes:
        raise HTTPException(status_code=413, detail="Attachment exceeds the configured size limit")
    checksum = hashlib.sha256(content).hexdigest()
    existing = session.scalar(
        select(Attachment).where(
            Attachment.organization_id == organization.id,
            Attachment.fuel_record_id == record.id,
            Attachment.kind == kind,
            Attachment.sha256 == checksum,
        )
    )
    if existing is not None:
        response.status_code = 200
        response.headers["Idempotency-Replayed"] = "true"
        return {"id": str(existing.id), "kind": existing.kind, "size_bytes": existing.size_bytes}
    try:
        key, size_bytes, checksum = store_image(
            content, upload.content_type or "", settings.attachment_directory
        )
    except ValueError as error:
        raise HTTPException(status_code=415, detail=str(error)) from None
    attachment = Attachment(
        organization_id=organization.id,
        fuel_record_id=record.id,
        uploaded_by_id=user.id,
        kind=kind,
        storage_key=key,
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        sha256=checksum,
    )
    session.add(attachment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        resolve_storage_key(key, settings.attachment_directory).unlink(missing_ok=True)
        existing = session.scalar(
            select(Attachment).where(
                Attachment.organization_id == organization.id,
                Attachment.fuel_record_id == record.id,
                Attachment.kind == kind,
                Attachment.sha256 == checksum,
            )
        )
        if existing is None:
            raise HTTPException(
                status_code=409, detail="Attachment could not be accepted"
            ) from None
        response.status_code = 200
        response.headers["Idempotency-Replayed"] = "true"
        return {"id": str(existing.id), "kind": existing.kind, "size_bytes": existing.size_bytes}
    except Exception:
        session.rollback()
        resolve_storage_key(key, settings.attachment_directory).unlink(missing_ok=True)
        raise
    return {"id": str(attachment.id), "kind": attachment.kind, "size_bytes": size_bytes}


@router.get("/{attachment_id}")
def download_attachment(
    record_id: UUID,
    attachment_id: UUID,
    user: CurrentUser,
    session: DatabaseSession,
) -> FileResponse:
    organization = get_user_organization(user, session)
    attachment = session.scalar(
        select(Attachment)
        .join(FuelRecord, Attachment.fuel_record_id == FuelRecord.id)
        .where(
            Attachment.id == attachment_id,
            Attachment.fuel_record_id == record_id,
            Attachment.organization_id == organization.id,
            FuelRecord.organization_id == organization.id,
        )
    )
    if attachment is None or (user.role == "DRIVER" and attachment.uploaded_by_id != user.id):
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = resolve_storage_key(attachment.storage_key, get_settings().attachment_directory)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path, media_type=attachment.content_type)
