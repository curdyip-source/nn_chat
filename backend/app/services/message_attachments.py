from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.schemas.message_attachments import MessageAttachmentUploadResponse

MESSAGE_ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024
ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif"}
ALLOWED_FILE_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}


@dataclass
class MessageAttachmentContent:
    content: bytes
    mime_type: str
    filename: str


class MessageAttachmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MessageAttachmentAssetRepository(db)

    async def upload_attachment(self, *, current_user: dict, file: UploadFile, attachment_kind: str) -> MessageAttachmentUploadResponse:
        normalized_kind = attachment_kind.strip().lower()
        if normalized_kind not in {"photo", "file"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неподдерживаемый тип вложения")

        filename = (file.filename or "attachment").strip() or "attachment"
        content = await file.read()
        mime_type = (file.content_type or "application/octet-stream").strip().lower()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл пустой")
        if len(content) > MESSAGE_ATTACHMENT_MAX_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл слишком большой")

        if normalized_kind == "photo":
            if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неподдерживаемый формат изображения")
        elif mime_type not in ALLOWED_FILE_MIME_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неподдерживаемый формат файла")

        row = self.repository.create(
            {
                "attachment_asset_owner_user_id": current_user["user_id"],
                "attachment_asset_storage_key": f"message-attachments/{current_user['user_id']}/{uuid4().hex}",
                "attachment_asset_original_filename": filename,
                "attachment_asset_mime_type": mime_type,
                "attachment_asset_kind": normalized_kind,
                "attachment_asset_size_bytes": len(content),
                "attachment_asset_bytes": content,
            }
        )
        return MessageAttachmentUploadResponse(
            attachment_kind=row.attachment_asset_kind,
            attachment_original_filename=row.attachment_asset_original_filename,
            attachment_mime_type=row.attachment_asset_mime_type,
            attachment_storage_key=row.attachment_asset_storage_key,
            attachment_size_bytes=row.attachment_asset_size_bytes,
        )

    def get_attachment_content(self, attachment_id: int) -> MessageAttachmentContent:
        row = self.repository.get_by_attachment_id(attachment_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
        return MessageAttachmentContent(
            content=row.attachment_asset_bytes,
            mime_type=row.attachment_asset_mime_type,
            filename=row.attachment_asset_original_filename,
        )


async def upload_message_attachment(db: Session, *, current_user: dict, file: UploadFile, attachment_kind: str) -> MessageAttachmentUploadResponse:
    return await MessageAttachmentService(db).upload_attachment(current_user=current_user, file=file, attachment_kind=attachment_kind)


def get_message_attachment_content(db: Session, attachment_id: int) -> MessageAttachmentContent:
    return MessageAttachmentService(db).get_attachment_content(attachment_id)