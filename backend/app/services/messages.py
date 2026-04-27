import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_MESSAGE, EVENT_TYPE_MESSAGE_CREATE, EVENT_TYPE_MESSAGE_DELETE, EVENT_TYPE_MESSAGE_UPDATE
from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.repositories.messages import MessageRepository
from app.repositories.user_devices import UserDeviceRepository
from app.schemas.common import build_pagination
from app.schemas.messages import MessageCreatePayload, MessageUpdatePayload
from app.services.audit import log_audit_event
from app.services.push_notifications import send_push_notification_event
from app.services.serializers import serialize_message


logger = logging.getLogger("app.messages")


class MessageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MessageRepository(db)
        self.attachment_asset_repository = MessageAttachmentAssetRepository(db)
        self.device_repository = UserDeviceRepository(db)

    def list_messages(self, *, before_message_id: int | None = None, page: int = 1, page_size: int = 50) -> dict:
        rows, total = self.repository.list(before_message_id=before_message_id, page=page, page_size=page_size)
        return {
            "items": [serialize_message(item) for item in rows],
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
        if row.message_owner_user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Можно управлять только своими сообщениями")
        if row.message_order_id or row.message_inventory_id or row.message_product_registration_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно удалить только обычное сообщение или сообщение с вложением")

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
        return serialize_message(updated_row)

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


def list_messages(db: Session, *, before_message_id: int | None = None, page: int = 1, page_size: int = 50) -> dict:
    return MessageService(db).list_messages(before_message_id=before_message_id, page=page, page_size=page_size)


def create_message(db: Session, payload: MessageCreatePayload, current_user: dict) -> dict:
    return MessageService(db).create_message(payload, current_user)


def update_message(db: Session, message_id: int, payload: MessageUpdatePayload, current_user: dict) -> dict:
    return MessageService(db).update_message(message_id, payload, current_user)


def delete_message(db: Session, message_id: int, current_user: dict) -> None:
    MessageService(db).delete_message(message_id, current_user)