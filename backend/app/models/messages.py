from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    message_order_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=True, index=True)
    message_inventory_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("inventories.inventory_id", ondelete="CASCADE"), nullable=True, index=True)
    message_product_registration_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("product_registrations.product_registration_id", ondelete="CASCADE"), nullable=True, index=True)
    message_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)
    # Bumped on any change to the message OR its referenced card (order/inventory/registration),
    # so delta-sync and SSE carry fresh statuses/items. Composite (updated_at, id) is the sync cursor.
    message_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), index=True)
    # Soft delete: kept so delta-sync can ship a tombstone and clients drop the row.
    message_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", back_populates="messages")
    order = relationship("Order", back_populates="messages")
    inventory = relationship("Inventory", back_populates="messages")
    product_registration = relationship("ProductRegistration", back_populates="messages")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    attachment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    attachment_message_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("messages.message_id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    attachment_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    attachment_mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    attachment_storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    attachment_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    message = relationship("Message", back_populates="attachments")
    owner = relationship("User", back_populates="message_attachments")