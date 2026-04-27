from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    order_establishment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("establishments.establishment_id", ondelete="RESTRICT"), nullable=False, index=True)
    order_method_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("order_methods.order_method_id", ondelete="RESTRICT"), nullable=False, index=True)
    order_sub_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_customer: Mapped[str] = mapped_column(String(255), nullable=False)
    order_info: Mapped[str] = mapped_column(Text, nullable=False)
    order_status_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("statuses.status_id", ondelete="RESTRICT"), nullable=False, index=True)
    order_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    order_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)

    establishment = relationship("Establishment", back_populates="orders")
    order_method = relationship("OrderMethod", back_populates="orders")
    status = relationship("Status", back_populates="orders")
    owner = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    comments = relationship("OrderComment", back_populates="order", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    order_item_order_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_product_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, index=True)
    order_item_name: Mapped[str] = mapped_column(String(500), nullable=False)
    order_item_article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_item_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_item_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    order_item_status_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("statuses.status_id", ondelete="SET NULL"), nullable=True, index=True)
    order_item_source_establishment_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("establishments.establishment_id", ondelete="SET NULL"), nullable=True, index=True)
    order_item_destination_establishment_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("establishments.establishment_id", ondelete="SET NULL"), nullable=True, index=True)
    order_item_currency_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("currencies.currency_id", ondelete="SET NULL"), nullable=True, index=True)
    order_item_checkpoint_started: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    order_item_checkpoint_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    order_item_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    status = relationship("Status", back_populates="order_items")
    source_establishment = relationship("Establishment", foreign_keys=[order_item_source_establishment_id], back_populates="source_order_items")
    destination_establishment = relationship("Establishment", foreign_keys=[order_item_destination_establishment_id], back_populates="destination_order_items")
    currency = relationship("Currency", back_populates="order_items")


class OrderComment(Base):
    __tablename__ = "order_comments"

    order_comment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    order_comment_order_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    order_comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    order_comment_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    order_comment_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    order = relationship("Order", back_populates="comments")
    owner = relationship("User", back_populates="order_comments")
    attachments = relationship("OrderCommentAttachment", back_populates="comment", cascade="all, delete-orphan")


class OrderCommentAttachment(Base):
    __tablename__ = "order_comment_attachments"

    attachment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    attachment_order_comment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("order_comments.order_comment_id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    attachment_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    attachment_mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    attachment_storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    attachment_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    comment = relationship("OrderComment", back_populates="attachments")
    owner = relationship("User", back_populates="order_comment_attachments")