from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class EstablishmentPayload(BaseModel):
    establishment_name: str = Field(min_length=1, max_length=255)
    establishment_address: Optional[str] = Field(default=None, max_length=2000)


class OrderMethodPayload(BaseModel):
    order_method_name: str = Field(min_length=1, max_length=255)
    order_method_sub_methods: Optional[list[str]] = Field(default=None)


class StatusPayload(BaseModel):
    status_type: str = Field(min_length=1, max_length=100)
    status_status: str = Field(min_length=1, max_length=255)
    status_color: Optional[str] = Field(default=None, max_length=50)


class CurrencyPayload(BaseModel):
    currency_name: str = Field(min_length=1, max_length=100)
    currency_sign: Optional[str] = Field(default=None, max_length=20)


class ProductCreatePayload(BaseModel):
    product_article: str = Field(min_length=1, max_length=100)
    product_name: str = Field(min_length=1, max_length=500)
    product_cost_usd: Decimal = Field(ge=0, decimal_places=2, max_digits=12)


class ProductUpdatePayload(BaseModel):
    product_article: Optional[str] = Field(default=None, min_length=1, max_length=100)
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    product_cost_usd: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, max_digits=12)