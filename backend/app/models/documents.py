from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    document_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    document_verified_by_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    document_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    document_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    document_storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    document_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    document_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    document_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", foreign_keys=[document_owner_user_id], back_populates="owned_documents")
    verified_by = relationship("User", foreign_keys=[document_verified_by_user_id], back_populates="verified_documents")