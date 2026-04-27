from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ProductRegistration(Base):
    __tablename__ = "product_registrations"

    product_registration_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    product_registration_establishment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("establishments.establishment_id", ondelete="RESTRICT"), nullable=False, index=True)
    product_registration_supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_registration_status_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("statuses.status_id", ondelete="RESTRICT"), nullable=False, index=True)
    product_registration_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    product_registration_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)

    establishment = relationship("Establishment", back_populates="product_registrations")
    status = relationship("Status", back_populates="product_registrations")
    owner = relationship("User", back_populates="product_registrations")
    items = relationship("ProductRegistrationItem", back_populates="product_registration", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="product_registration")


class ProductRegistrationItem(Base):
    __tablename__ = "product_registration_items"

    product_registration_item_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    product_registration_item_product_registration_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("product_registrations.product_registration_id", ondelete="CASCADE"), nullable=False, index=True)
    product_registration_item_product_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, index=True)
    product_registration_item_name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_registration_item_article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_registration_item_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    product_registration_item_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_registration_item_currency_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("currencies.currency_id", ondelete="SET NULL"), nullable=True, index=True)
    product_registration_item_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    product_registration_item_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    product_registration = relationship("ProductRegistration", back_populates="items")
    product = relationship("Product", back_populates="product_registration_items")
    currency = relationship("Currency", back_populates="product_registration_items")