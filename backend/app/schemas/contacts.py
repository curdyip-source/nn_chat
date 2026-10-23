from typing import Optional

from pydantic import BaseModel, Field


class ContactUpdatePayload(BaseModel):
    # Полная карточка контрагента (PUT). Для поставщика значимы только имя и инфо.
    contact_name: str = Field(min_length=1, max_length=255)
    contact_info: Optional[str] = None
    contact_establishment_id: Optional[int] = None
    contact_order_method_id: Optional[int] = None
    contact_order_sub_method: Optional[str] = Field(default=None, max_length=255)
    contact_contact_method: Optional[str] = Field(default=None, max_length=50)
    contact_sales_channel: Optional[str] = Field(default=None, max_length=50)
