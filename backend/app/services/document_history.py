"""История инвентаризаций и приёмок — по событиям аудита, в том же формате, что
история заказа (GET /orders/{id}/history), чтобы приложение рисовало её одним окном."""

from sqlalchemy.orm import Session

from app.models.reference_data import Status
from app.repositories.audit_events import AuditEventRepository
from app.services.serializers import serialize_datetime


def history_actor(event) -> tuple[str | None, str]:
    # ФИО актора (как в чате: «Фамилия Имя»), fallback — логин, затем «Система».
    actor = getattr(event, "actor", None)
    if actor is None:
        return None, "Система"
    full = " ".join(part for part in (actor.user_second_name, actor.user_first_name) if part).strip()
    return actor.user_login, (full or actor.user_login or "Пользователь")


def build_document_history(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    status_field: str,
    noun: str,
) -> dict:
    """Лента событий документа, новые сверху.

    update-события бывают двух видов: смена статуса (в payload только `status_field`
    с id статуса) и полная правка документа (payload с items_count). noun — документ
    в винительном падеже для текста («создал инвентаризацию»).
    """
    rows, _ = AuditEventRepository(db).list(
        actor_user_id=None, entity_type=entity_type, entity_id=entity_id,
        event_type=None, date_from=None, date_to=None, page=1, page_size=500,
    )
    rows = sorted(rows, key=lambda event: (event.created_at, event.audit_event_id), reverse=True)

    # В payload смены статуса лежит только id — названия подтягиваем одним запросом.
    status_ids = {
        (event.event_payload or {}).get(status_field)
        for event in rows
        if (event.event_payload or {}).get(status_field)
    }
    status_names = {
        row.status_id: row.status_status
        for row in db.query(Status).filter(Status.status_id.in_(status_ids)).all()
    } if status_ids else {}

    items = []
    for event in rows:
        payload = event.event_payload or {}
        action = event.event_type.rsplit(".", 1)[-1]
        if action == "create":
            kind, text = "create", f"создал {noun}"
        elif action == "delete":
            kind, text = "delete", f"удалил {noun}"
        elif action == "update" and payload.get(status_field):
            name = status_names.get(payload[status_field])
            kind, text = "status", f"сменил статус на «{name}»" if name else "сменил статус"
        elif action == "update":
            kind, text = "edit", f"отредактировал {noun}"
        else:
            continue
        actor_login, actor_name = history_actor(event)
        items.append({
            "audit_event_id": event.audit_event_id,
            "kind": kind,
            "text": text,
            "actor_user_login": actor_login,
            "actor_name": actor_name,
            "created_at": serialize_datetime(event.created_at),
        })
    return {"items": items}
