from datetime import datetime

from sqlalchemy.orm import Session

from app.core.request_context import get_request_context
from app.repositories.audit_events import AuditEventRepository
from app.schemas.audit import AuditEventCreatePayload
from app.schemas.common import build_pagination
from app.services.serializers import serialize_audit_event


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repository = AuditEventRepository(db)

    def log_event(self, payload: AuditEventCreatePayload) -> dict:
        row = self.repository.create(payload.model_dump())
        return serialize_audit_event(row)

    def list_events(
        self,
        *,
        actor_user_id: int | None,
        entity_type: str | None,
        entity_id: int | None,
        event_type: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> dict:
        rows, total = self.repository.list(
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        return {
            "items": [serialize_audit_event(row) for row in rows],
            "pagination": build_pagination(page, page_size, total),
            "filters": {
                "actor_user_id": actor_user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_type": event_type,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
        }


def log_audit_event(
    db: Session,
    *,
    actor_user_id: int | None,
    entity_type: str,
    entity_id: int | None,
    event_type: str,
    event_payload: dict | None = None,
) -> dict:
    request_context = get_request_context()
    payload = AuditEventCreatePayload(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        event_payload=event_payload,
        request_id=request_context["request_id"],
        ip_address=request_context["ip_address"],
        user_agent=request_context["user_agent"],
    )
    return AuditService(db).log_event(payload)


def list_audit_events(
    db: Session,
    *,
    actor_user_id: int | None,
    entity_type: str | None,
    entity_id: int | None,
    event_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    page_size: int,
) -> dict:
    return AuditService(db).list_events(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )