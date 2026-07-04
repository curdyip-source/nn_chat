from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("user_age >= 0", name="ck_users_user_age_non_negative"),)

    user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    user_login: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_password: Mapped[str] = mapped_column(Text, nullable=False)
    user_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=func.false())
    # Разрешённые разделы меню (ось A). NULL = все операционные разделы; список = только эти.
    user_sections: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    user_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_second_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_profile_photo: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_age: Mapped[int] = mapped_column(Integer, nullable=False)
    user_address: Mapped[str] = mapped_column(Text, nullable=False)
    user_verified_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    user_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    owned_documents = relationship("Document", foreign_keys="Document.document_owner_user_id", back_populates="owner", cascade="all, delete-orphan")
    verified_documents = relationship("Document", foreign_keys="Document.document_verified_by_user_id", back_populates="verified_by")
    audit_events = relationship("AuditEvent", back_populates="actor")
    verified_by = relationship("User", remote_side=[user_id], foreign_keys=[user_verified_user_id], back_populates="verified_users")
    verified_users = relationship("User", foreign_keys=[user_verified_user_id], back_populates="verified_by")
    messages = relationship("Message", back_populates="owner", cascade="all, delete-orphan")
    message_attachments = relationship("MessageAttachment", back_populates="owner")
    profile_photo_asset = relationship("ProfilePhoto", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="owner")
    order_comments = relationship("OrderComment", back_populates="owner")
    order_comment_attachments = relationship("OrderCommentAttachment", back_populates="owner")
    inventories = relationship("Inventory", back_populates="owner")
    product_registrations = relationship("ProductRegistration", back_populates="owner")
    user_devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    establishment_roles = relationship("UserEstablishmentRole", back_populates="user", cascade="all, delete-orphan")
    owned_establishments = relationship("Establishment", back_populates="owner")
    owned_order_methods = relationship("OrderMethod", back_populates="owner")
    owned_statuses = relationship("Status", back_populates="owner")
    owned_currencies = relationship("Currency", back_populates="owner")
    owned_products = relationship("Product", back_populates="owner")
    owned_contacts = relationship("Contact", back_populates="owner")