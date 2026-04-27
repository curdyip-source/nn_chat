from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.services.message_attachments import MessageAttachmentContent


class OrderCommentAttachmentService:
    def __init__(self, db) -> None:
        self.repository = MessageAttachmentAssetRepository(db)

    def get_attachment_content(self, attachment_id: int) -> MessageAttachmentContent:
        row = self.repository.get_by_order_comment_attachment_id(attachment_id)
        if row is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
        return MessageAttachmentContent(
            content=row.attachment_asset_bytes,
            mime_type=row.attachment_asset_mime_type,
            filename=row.attachment_asset_original_filename,
        )


def get_order_comment_attachment_content(db, attachment_id: int) -> MessageAttachmentContent:
    return OrderCommentAttachmentService(db).get_attachment_content(attachment_id)
