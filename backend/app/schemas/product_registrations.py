from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ProductRegistrationItemCreatePayload(BaseModel):
    product_id: Optional[int] = Field(default=None, ge=1)
    product_article: Optional[str] = Field(default=None, min_length=1, max_length=100)
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    product_registration_item_quantity: int = Field(ge=1)
    product_registration_item_cost: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    product_registration_item_currency_id: Optional[int] = Field(default=None, ge=1)
    # Вес одной штуки, кг. Ключа нет в запросе — при правке остаётся прежний вес
    # (веб про вес не знает), явный null — очистить.
    product_registration_item_weight: Optional[Decimal] = Field(default=None, gt=0, decimal_places=3, max_digits=10)


class ProductRegistrationCreatePayload(BaseModel):
    product_registration_establishment_id: int = Field(ge=1)
    product_registration_supplier: str = Field(min_length=1, max_length=255)
    save_contact: bool = False
    product_registration_status_id: Optional[int] = Field(default=None, ge=1)
    product_registration_shipping_cost: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    product_registration_shipping_currency_id: Optional[int] = Field(default=None, ge=1)
    message_text: Optional[str] = Field(default=None, max_length=4000)
    items: list[ProductRegistrationItemCreatePayload] = Field(min_length=1)


class ProductRegistrationUpdatePayload(BaseModel):
    product_registration_establishment_id: int = Field(ge=1)
    product_registration_supplier: str = Field(min_length=1, max_length=255)
    product_registration_status_id: Optional[int] = Field(default=None, ge=1)
    # Как и вес: ключа нет — доставка остаётся прежней, явный null — очистить.
    product_registration_shipping_cost: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    product_registration_shipping_currency_id: Optional[int] = Field(default=None, ge=1)
    items: list[ProductRegistrationItemCreatePayload] = Field(min_length=1)


class ProductRegistrationStatusUpdatePayload(BaseModel):
    product_registration_status_id: int = Field(ge=1)