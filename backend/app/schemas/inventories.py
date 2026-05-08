from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class InventoryItemCreatePayload(BaseModel):
    product_id: Optional[int] = Field(default=None, ge=1)
    product_article: Optional[str] = Field(default=None, min_length=1, max_length=100)
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    inventory_item_quantity: int = Field(ge=1)
    inventory_item_cost: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    inventory_item_currency_id: Optional[int] = Field(default=None, ge=1)


class InventoryCreatePayload(BaseModel):
    inventory_establishment_id: int = Field(ge=1)
    inventory_supplier: Optional[str] = Field(default=None, min_length=1, max_length=255)
    save_contact: bool = False
    inventory_status_id: Optional[int] = Field(default=None, ge=1)
    message_text: Optional[str] = Field(default=None, max_length=4000)
    items: list[InventoryItemCreatePayload] = Field(min_length=1)


class InventoryStatusUpdatePayload(BaseModel):
    inventory_status_id: int = Field(ge=1)