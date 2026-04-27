from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class MessageAttachmentAsset(Base):
    __tablename__ = "message_attachment_assets"

    attachment_asset_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    attachment_asset_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_asset_storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    attachment_asset_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    attachment_asset_mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    attachment_asset_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    attachment_asset_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    attachment_asset_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    attachment_asset_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)

    owner = relationship("User")