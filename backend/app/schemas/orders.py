from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.messages import MessageAttachmentCreatePayload


class OrderItemCreatePayload(BaseModel):
    product_id: Optional[int] = Field(default=None, ge=1)
    product_article: Optional[str] = Field(default=None, min_length=1, max_length=100)
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    order_item_quantity: int = Field(ge=1)
    order_item_price: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    order_item_status_id: Optional[int] = Field(default=None, ge=1)
    order_item_supplier: Optional[str] = Field(default=None, min_length=1, max_length=255)
    order_item_note: Optional[str] = Field(default=None, max_length=255)
    order_item_source_establishment_id: Optional[int] = Field(default=None, ge=1)
    order_item_destination_establishment_id: Optional[int] = Field(default=None, ge=1)
    order_item_currency_id: Optional[int] = Field(default=None, ge=1)
    order_item_checkpoint_started: bool = False
    order_item_checkpoint_completed: bool = False


class OrderCdekPayload(BaseModel):
    """Данные СДЭК, заполняемые при создании заказа (метод СДЭК) — сохраняются в заказ."""
    recipient_name: Optional[str] = Field(default=None, max_length=255)
    recipient_phone: Optional[str] = Field(default=None, max_length=50)
    city_code: Optional[int] = Field(default=None, ge=1)
    city_name: Optional[str] = Field(default=None, max_length=255)
    delivery_mode: Optional[str] = Field(default=None, pattern="^(pvz|door)$")
    pvz_code: Optional[str] = Field(default=None, max_length=50)
    pvz_address: Optional[str] = Field(default=None, max_length=500)
    delivery_address: Optional[str] = Field(default=None, max_length=500)


class OrderCreatePayload(BaseModel):
    order_establishment_id: int = Field(ge=1)
    order_method_id: int = Field(ge=1)
    order_sub_method: Optional[str] = Field(default=None, min_length=1, max_length=255)
    order_contact_method: Optional[str] = Field(default=None, min_length=1, max_length=50)
    order_customer: str = Field(min_length=1, max_length=255)
    order_info: str = Field(default="", max_length=4000)
    save_contact: bool = False
    order_status_id: Optional[int] = Field(default=None, ge=1)
    message_text: Optional[str] = Field(default=None, max_length=4000)
    cdek: Optional[OrderCdekPayload] = None
    items: list[OrderItemCreatePayload] = Field(min_length=1)


class OrderStatusUpdatePayload(BaseModel):
    order_status_id: int = Field(ge=1)


class OrderUpdatePayload(BaseModel):
    order_establishment_id: int = Field(ge=1)
    order_method_id: int = Field(ge=1)
    order_sub_method: Optional[str] = Field(default=None, min_length=1, max_length=255)
    order_contact_method: Optional[str] = Field(default=None, min_length=1, max_length=50)
    order_customer: str = Field(min_length=1, max_length=255)
    order_info: str = Field(default="", max_length=4000)
    order_status_id: int = Field(ge=1)
    items: list[OrderItemCreatePayload] = Field(min_length=1)


class OrderCommentCreatePayload(BaseModel):
    order_comment_text: Optional[str] = Field(default=None, max_length=4000)
    attachments: list[MessageAttachmentCreatePayload] = Field(default_factory=list)
    mentioned_user_ids: list[int] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_comment(self):
        if not (self.order_comment_text and self.order_comment_text.strip()) and not self.attachments:
            raise ValueError("Текст комментария или вложение обязательны")
        return self


class OrderCommentUpdatePayload(BaseModel):
    order_comment_text: str = Field(min_length=1, max_length=4000)
    mentioned_user_ids: list[int] = Field(default_factory=list, max_length=100)