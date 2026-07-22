from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Establishment(Base):
    __tablename__ = "establishments"
    __table_args__ = (UniqueConstraint("establishment_name", name="uq_establishments_name"),)

    establishment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    establishment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    establishment_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    establishment_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    establishment_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="owned_establishments")
    orders = relationship("Order", back_populates="establishment")
    source_order_items = relationship("OrderItem", foreign_keys="OrderItem.order_item_source_establishment_id", back_populates="source_establishment")
    destination_order_items = relationship("OrderItem", foreign_keys="OrderItem.order_item_destination_establishment_id", back_populates="destination_establishment")
    inventories = relationship("Inventory", back_populates="establishment")
    product_registrations = relationship("ProductRegistration", back_populates="establishment")
    contacts = relationship("Contact", back_populates="establishment")
    user_roles = relationship("UserEstablishmentRole", back_populates="establishment", cascade="all, delete-orphan")


class OrderMethod(Base):
    __tablename__ = "order_methods"
    __table_args__ = (UniqueConstraint("order_method_name", name="uq_order_methods_name"),)

    order_method_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    order_method_name: Mapped[str] = mapped_column(String(255), nullable=False)
    order_method_sub_methods: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    order_method_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    order_method_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="owned_order_methods")
    orders = relationship("Order", back_populates="order_method")
    contacts = relationship("Contact", back_populates="order_method")


class OrderSalesChannel(Base):
    __tablename__ = "order_sales_channels"
    __table_args__ = (UniqueConstraint("order_sales_channel_name", name="uq_order_sales_channels_name"),)

    order_sales_channel_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    order_sales_channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    order_sales_channel_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    order_sales_channel_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class Status(Base):
    __tablename__ = "statuses"
    __table_args__ = (UniqueConstraint("status_type", "status_status", name="uq_statuses_type_name"),)

    status_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    status_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status_status: Mapped[str] = mapped_column(String(255), nullable=False)
    status_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    status_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="owned_statuses")
    orders = relationship("Order", back_populates="status")
    order_items = relationship("OrderItem", back_populates="status")
    inventories = relationship("Inventory", back_populates="status")
    product_registrations = relationship("ProductRegistration", back_populates="status")


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("currency_name", name="uq_currencies_name"),)

    currency_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    currency_name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency_sign: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    currency_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="owned_currencies")
    order_items = relationship("OrderItem", back_populates="currency")
    inventory_items = relationship("InventoryItem", back_populates="currency")
    product_registration_items = relationship("ProductRegistrationItem", back_populates="currency")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("product_article", name="uq_products_article"),)

    product_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    product_article: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    product_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    product_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="owned_products")
    order_items = relationship("OrderItem", back_populates="product")
    inventory_items = relationship("InventoryItem", back_populates="product")
    product_registration_items = relationship("ProductRegistrationItem", back_populates="product")