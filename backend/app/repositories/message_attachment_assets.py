from sqlalchemy.orm import Session

from app.models.message_attachment_assets import MessageAttachmentAsset
from app.models.messages import MessageAttachment
from app.models.orders import OrderCommentAttachment


class MessageAttachmentAssetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> MessageAttachmentAsset:
        row = MessageAttachmentAsset(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_storage_key(self, storage_key: str) -> MessageAttachmentAsset | None:
        return (
            self.db.query(MessageAttachmentAsset)
            .filter(MessageAttachmentAsset.attachment_asset_storage_key == storage_key)
            .first()
        )

    def get_by_attachment_id(self, attachment_id: int) -> MessageAttachmentAsset | None:
        return (
            self.db.query(MessageAttachmentAsset)
            .join(
                MessageAttachment,
                MessageAttachment.attachment_storage_key == MessageAttachmentAsset.attachment_asset_storage_key,
            )
            .filter(MessageAttachment.attachment_id == attachment_id)
            .first()
        )

    def get_by_order_comment_attachment_id(self, attachment_id: int) -> MessageAttachmentAsset | None:
        return (
            self.db.query(MessageAttachmentAsset)
            .join(
                OrderCommentAttachment,
                OrderCommentAttachment.attachment_storage_key == MessageAttachmentAsset.attachment_asset_storage_key,
            )
            .filter(OrderCommentAttachment.attachment_id == attachment_id)
            .first()
        )