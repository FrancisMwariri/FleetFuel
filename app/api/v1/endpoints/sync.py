from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession, get_user_organization
from app.models.entities import FuelRecord
from app.schemas.fuel import FuelRecordCreate
from app.services.fuel import create_fuel_record

router = APIRouter(prefix="/sync", tags=["synchronization"])


@router.post("/fuel-records")
def sync_fuel_records(
    payload: list[object],
    user: CurrentUser,
    session: DatabaseSession,
) -> dict[str, list[dict[str, object]]]:
    if len(payload) > 50:
        raise HTTPException(status_code=413, detail="A sync batch may contain at most 50 records")
    organization = get_user_organization(user, session)
    results: list[dict[str, object]] = []
    for raw_record in payload:
        if not isinstance(raw_record, dict):
            results.append(
                {
                    "client_record_id": None,
                    "status": "rejected_validation",
                    "error": "Record must be an object",
                }
            )
            continue
        client_record_id = raw_record.get("client_record_id")
        try:
            record_payload = FuelRecordCreate.model_validate(raw_record).model_copy(
                update={"source": "OFFLINE"}
            )
        except ValidationError as error:
            results.append(
                {
                    "client_record_id": str(client_record_id) if client_record_id else None,
                    "status": "rejected_validation",
                    "errors": error.errors(include_url=False),
                }
            )
            continue

        try:
            with session.begin_nested():
                record, replayed = create_fuel_record(
                    session,
                    user=user,
                    organization=organization,
                    payload=record_payload,
                )
                session.flush()
            results.append(
                {
                    "client_record_id": str(record.client_record_id),
                    "record_id": str(record.id),
                    "status": "already_accepted" if replayed else "accepted",
                    "received_at": record.received_at.isoformat(),
                }
            )
        except HTTPException as error:
            status_name = (
                "rejected_authorization"
                if error.status_code in {401, 403, 404}
                else "rejected_validation"
            )
            results.append(
                {
                    "client_record_id": str(record_payload.client_record_id),
                    "status": status_name,
                    "status_code": error.status_code,
                    "error": error.detail,
                }
            )
        except IntegrityError:
            duplicate = session.scalar(
                select(FuelRecord).where(
                    FuelRecord.organization_id == organization.id,
                    FuelRecord.client_record_id == record_payload.client_record_id,
                )
            )
            results.append(
                {
                    "client_record_id": str(record_payload.client_record_id),
                    "record_id": str(duplicate.id) if duplicate else None,
                    "status": "already_accepted" if duplicate else "failed_temporarily",
                    "retryable": duplicate is None,
                }
            )
    session.commit()
    return {"results": results}
