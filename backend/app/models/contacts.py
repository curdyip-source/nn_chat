from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Contact(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_establishment_id: Mapped[int | None] = mapped_column(
        SQL_ID_TYPE,
        ForeignKey("establishments.establishment_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_order_method_id: Mapped[int | None] = mapped_column(
        SQL_ID_TYPE,
        ForeignKey("order_methods.order_method_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_order_sub_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_owner_user_id: Mapped[int | None] = mapped_column(
        SQL_ID_TYPE,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)

    establishment = relationship("Establishment", back_populates="contacts")
    order_method = relationship("OrderMethod", back_populates="contacts")
    owner = relationship("User", back_populates="owned_contacts")