from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.models.audit_events import AuditEvent


class AuditEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> AuditEvent:
        row = AuditEvent(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.audit_event_id)

    def get_by_id(self, audit_event_id: int) -> AuditEvent | None:
        return (
            self.db.query(AuditEvent)
            .options(joinedload(AuditEvent.actor))
            .filter(AuditEvent.audit_event_id == audit_event_id)
            .first()
        )

    def list(
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
    ) -> tuple[list[AuditEvent], int]:
        query = self.db.query(AuditEvent).options(joinedload(AuditEvent.actor))

        if actor_user_id is not None:
            query = query.filter(AuditEvent.actor_user_id == actor_user_id)
        if entity_type:
            query = query.filter(AuditEvent.entity_type == entity_type)
        if entity_id is not None:
            query = query.filter(AuditEvent.entity_id == entity_id)
        if event_type:
            query = query.filter(AuditEvent.event_type == event_type)
        if date_from is not None:
            query = query.filter(AuditEvent.created_at >= date_from)
        if date_to is not None:
            query = query.filter(AuditEvent.created_at <= date_to)

        total = query.count()
        items = (
            query.order_by(desc(AuditEvent.created_at), desc(AuditEvent.audit_event_id))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total