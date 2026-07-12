import base64
import binascii
import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_MESSAGE, EVENT_TYPE_MESSAGE_CREATE, EVENT_TYPE_MESSAGE_DELETE, EVENT_TYPE_MESSAGE_UPDATE
from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.repositories.messages import MessageRepository
from app.repositories.user_devices import UserDeviceRepository
from app.repositories.users import UserRepository
from app.schemas.common import build_pagination
from app.schemas.messages import MessageCreatePayload, MessageUpdatePayload
from app.services.access_control import allowed_order_status_ids, list_visibility
from app.services.audit import log_audit_event
from app.services.message_stream import broker
from app.services.push_notifications import send_mention_push_event, send_push_notification_event
from app.services.serializers import serialize_message, serialize_message_tombstone


def _encode_sync_cursor(updated_at: datetime, message_id: int) -> str:
    raw = f"{updated_at.isoformat()}|{message_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_sync_cursor(cursor: str | None) -> tuple[datetime | None, int | None]:
    if not cursor:
        return None, None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        iso, _, message_id = raw.rpartition("|")
        return datetime.fromisoformat(iso), int(message_id)
    except (ValueError, binascii.Error):
        # A malformed cursor falls back to a full sync rather than failing the request.
        return None, None


def _card_establishment_owner(row) -> tuple[int, int] | None:
    """(establishment_id, owner_user_id) встроенной карточки-документа, либо None для
    обычного текстового сообщения (общего для всех в чате)."""
    if row.message_order_id is not None and row.order is not None:
        return row.order.order_establishment_id, row.order.order_owner_user_id
    if row.message_inventory_id is not None and row.inventory is not None:
        return row.inventory.inventory_establishment_id, row.inventory.inventory_owner_user_id
    if row.message_product_registration_id is not None and row.product_registration is not None:
        return (
            row.product_registration.product_registration_establishment_id,
            row.product_registration.product_registration_owner_user_id,
        )
    return None


def _card_visibility_predicate(db: Session, current_user: dict):
    """Предикат видимости карточки для ленты чата. list_visibility считаем ОДИН раз (а не
    запрос на каждую строку). Обычные сообщения и tombstone — всегда видимы; карточки —
    по правам склада (склад ∈ full ИЛИ (склад ∈ own И владелец=я)) и, для заказов,
    дополнительно по статусу заказа (ось C) — иначе отгрузочный юзер видел бы в чате
    карточки заказов в любом статусе."""
    full_ids, own_ids, uid = list_visibility(db, current_user)
    if full_ids is None:
        return lambda row: True  # админ — обходит фильтрацию
    allowed_statuses = allowed_order_status_ids(current_user)

    def _visible(row) -> bool:
        scope = _card_establishment_owner(row)
        if scope is None:
            return True
        establishment_id, owner_user_id = scope
        if not (establishment_id in full_ids or (establishment_id in own_ids and owner_user_id == uid)):
            return False
        if allowed_statuses is not None and row.message_order_id is not None and row.order is not None:
            return row.order.order_status_id in allowed_statuses
        return True

    return _visible


def sync_messages(db: Session, current_user: dict, *, cursor: str | None, limit: int) -> dict:
    since_updated_at, since_message_id = _decode_sync_cursor(cursor)
    rows = MessageRepository(db).list_changes(
        since_updated_at=since_updated_at,
        since_message_id=since_message_id,
        limit=limit,
    )
    # Карточки заказов/инвентаризаций/приёмок фильтруем по доступу к складу (как в списках).
    # Курсор считаем по ПОЛНОМУ набору строк (не по видимым) — пагинация не ломается.
    visible = _card_visibility_predicate(db, current_user)
    items: list[dict] = []
    for row in rows:
        if row.message_deleted_at is not None:
            items.append(serialize_message_tombstone(row))
        elif visible(row):
            items.append(serialize_message(row))
    if rows:
        last = rows[-1]
        next_cursor = _encode_sync_cursor(last.message_updated_at, last.message_id)
    else:
        next_cursor = cursor or ""
    return {"items": items, "cursor": next_cursor, "has_more": len(rows) == limit}


def resolve_mention_recipient_ids(db: Session, *, mentioned_user_ids: list[int], sender_user_id: int) -> list[int]:
    unique_ids = {user_id for user_id in mentioned_user_ids if user_id != sender_user_id}
    if not unique_ids:
        return []
    active_rows = UserRepository(db).list_active_by_ids(list(unique_ids))
    return [row.user_id for row in active_rows]


logger = logging.getLogger("app.messages")


class MessageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MessageRepository(db)
        self.attachment_asset_repository = MessageAttachmentAssetRepository(db)
        self.device_repository = UserDeviceRepository(db)

    def list_messages(self, current_user: dict, *, before_message_id: int | None = None, page: int = 1, page_size: int = 50) -> dict:
        rows, total = self.repository.list(before_message_id=before_message_id, page=page, page_size=page_size)
        visible = _card_visibility_predicate(self.db, current_user)
        return {
            "items": [serialize_message(item) for item in rows if visible(item)],
            "pagination": build_pagination(page, page_size, total),
            "filters": {"before_message_id": before_message_id},
        }

    def get_message_or_404(self, message_id: int):
        row = self.repository.get_by_id(message_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
        return row

    def _ensure_manageable_plain_message(self, row, current_user: dict) -> None:
        if row.message_owner_user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Можно управлять только своими сообщениями")
        if row.message_type != "message" or row.message_order_id or row.message_inventory_id or row.message_product_registration_id or row.attachments:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно изменить или удалить только обычное текстовое сообщение")

    def _ensure_deletable_chat_message(self, row, current_user: dict) -> None:
        # Карточки заказа/инвентаризации/приёмки этим путём не удаляются (ни
        # владельцем, ни админом) — они убираются вместе со своей сущностью.
        if row.message_order_id or row.message_inventory_id or row.message_product_registration_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно удалить только обычное сообщение или сообщение с вложением")
        # Своё сообщение удаляет владелец; чужие обычные чат-сообщения — только админ.
        if row.message_owner_user_id != current_user["user_id"] and not current_user["user_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Удалять чужие сообщения может только администратор")

    def create_message(self, payload: MessageCreatePayload, current_user: dict) -> dict:
        attachments = []
        for item in payload.attachments:
            asset = self.attachment_asset_repository.get_by_storage_key(item.attachment_storage_key)
            if asset is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вложение не найдено")
            if asset.attachment_asset_owner_user_id != current_user["user_id"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для вложения")
            if asset.attachment_asset_kind != item.attachment_kind:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Тип вложения не совпадает")

            attachments.append(
                {
                    "attachment_owner_user_id": current_user["user_id"],
                    "attachment_kind": asset.attachment_asset_kind,
                    "attachment_original_filename": asset.attachment_asset_original_filename,
                    "attachment_mime_type": asset.attachment_asset_mime_type,
                    "attachment_storage_key": asset.attachment_asset_storage_key,
                    "attachment_size_bytes": asset.attachment_asset_size_bytes,
                }
            )

        row = self.repository.create(
            {
                "message_type": payload.message_type,
                "message_text": payload.message_text.strip() if payload.message_text else None,
                "message_owner_user_id": current_user["user_id"],
            },
            attachments=attachments,
        )
        targets = self.device_repository.list_active_for_other_users(excluded_user_id=current_user["user_id"])
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_MESSAGE,
            entity_id=row.message_id,
            event_type=EVENT_TYPE_MESSAGE_CREATE,
            event_payload={
                "message_type": row.message_type,
                "message_text": row.message_text,
                "attachments_count": len(row.attachments),
                "notification_target_count": len(targets),
            },
        )
        result = serialize_message(row)
        result["notification_target_count"] = len(targets)

        broker.publish({"type": "created", "message": serialize_message(row)})

        try:
            send_push_notification_event(
                self.db,
                excluded_user_id=current_user["user_id"],
                message_type=row.message_type,
                sender_name=f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"],
                message_text=row.message_text,
                entity_id=row.message_id,
            )
        except Exception:
            logger.exception(
                "push.dispatch_failed",
                extra={
                    "event_type": "push.dispatch_failed",
                    "message_id": row.message_id,
                    "message_type": row.message_type,
                    "user_id": current_user["user_id"],
                },
            )

        try:
            mention_recipient_ids = resolve_mention_recipient_ids(
                self.db,
                mentioned_user_ids=payload.mentioned_user_ids,
                sender_user_id=current_user["user_id"],
            )
            if mention_recipient_ids:
                send_mention_push_event(
                    self.db,
                    recipient_user_ids=mention_recipient_ids,
                    sender_name=f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"],
                    context="chat",
                    entity_id=row.message_id,
                )
        except Exception:
            logger.exception(
                "push.mention_dispatch_failed",
                extra={
                    "event_type": "push.mention_dispatch_failed",
                    "message_id": row.message_id,
                    "user_id": current_user["user_id"],
                },
            )

        return result

    def update_message(self, message_id: int, payload: MessageUpdatePayload, current_user: dict) -> dict:
        row = self.get_message_or_404(message_id)
        self._ensure_manageable_plain_message(row, current_user)
        updated_row = self.repository.update(row, {"message_text": payload.message_text.strip()})
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_MESSAGE,
            entity_id=updated_row.message_id,
            event_type=EVENT_TYPE_MESSAGE_UPDATE,
            event_payload={
                "message_type": updated_row.message_type,
                "previous_message_text": row.message_text,
                "message_text": updated_row.message_text,
            },
        )
        result = serialize_message(updated_row)
        broker.publish({"type": "updated", "message": result})
        return result

    def delete_message(self, message_id: int, current_user: dict) -> None:
        row = self.get_message_or_404(message_id)
        self._ensure_deletable_chat_message(row, current_user)
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_MESSAGE,
            entity_id=row.message_id,
            event_type=EVENT_TYPE_MESSAGE_DELETE,
            event_payload={
                "message_type": row.message_type,
                "message_text": row.message_text,
                "attachments_count": len(row.attachments),
            },
        )
        self.repository.delete(row)
        broker.publish({"type": "deleted", "message_id": message_id})


def list_messages(db: Session, current_user: dict, *, before_message_id: int | None = None, page: int = 1, page_size: int = 50) -> dict:
    return MessageService(db).list_messages(current_user, before_message_id=before_message_id, page=page, page_size=page_size)


def create_message(db: Session, payload: MessageCreatePayload, current_user: dict) -> dict:
    return MessageService(db).create_message(payload, current_user)


def update_message(db: Session, message_id: int, payload: MessageUpdatePayload, current_user: dict) -> dict:
    return MessageService(db).update_message(message_id, payload, current_user)


def delete_message(db: Session, message_id: int, current_user: dict) -> None:
    MessageService(db).delete_message(message_id, current_user)