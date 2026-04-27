from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Inventory(Base):
    __tablename__ = "inventories"

    inventory_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    inventory_establishment_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("establishments.establishment_id", ondelete="RESTRICT"), nullable=False, index=True)
    inventory_supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inventory_status_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("statuses.status_id", ondelete="RESTRICT"), nullable=False, index=True)
    inventory_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)

    establishment = relationship("Establishment", back_populates="inventories")
    status = relationship("Status", back_populates="inventories")
    owner = relationship("User", back_populates="inventories")
    items = relationship("InventoryItem", back_populates="inventory", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="inventory")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    inventory_item_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    inventory_item_inventory_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("inventories.inventory_id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_product_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True, index=True)
    inventory_item_name: Mapped[str] = mapped_column(String(500), nullable=False)
    inventory_item_article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    inventory_item_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    inventory_item_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    inventory_item_currency_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("currencies.currency_id", ondelete="SET NULL"), nullable=True, index=True)
    inventory_item_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    inventory = relationship("Inventory", back_populates="items")
    product = relationship("Product", back_populates="inventory_items")
    currency = relationship("Currency", back_populates="inventory_items")