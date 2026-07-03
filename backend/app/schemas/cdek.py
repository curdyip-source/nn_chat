from typing import Optional

from pydantic import BaseModel, Field


class CdekPackage(BaseModel):
    weight: int = Field(default=500, ge=1, description="Вес, граммы")
    length: int = Field(default=20, ge=1, description="см")
    width: int = Field(default=15, ge=1, description="см")
    height: int = Field(default=10, ge=1, description="см")


class CdekWaybillCreate(BaseModel):
    tariff_code: int = Field(ge=1)
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=5, max_length=50)
    from_city_code: Optional[int] = Field(default=None, ge=1, description="Город отправителя (origin); None → дефолт из конфига (Москва)")
    from_city_name: Optional[str] = Field(default=None, max_length=255)
    city_code: int = Field(ge=1)
    city_name: Optional[str] = Field(default=None, max_length=255)
    delivery_mode: str = Field(default="pvz", pattern="^(pvz|door)$")
    pvz_code: Optional[str] = Field(default=None, max_length=50)         # для delivery_mode=pvz
    pvz_address: Optional[str] = Field(default=None, max_length=500)     # адрес ПВЗ (для отображения)
    delivery_address: Optional[str] = Field(default=None, max_length=500)  # для delivery_mode=door
    package: CdekPackage = Field(default_factory=CdekPackage)
    comment: Optional[str] = Field(default=None, max_length=255)
    save_to_contact: bool = Field(default=True, description="Сохранить данные СДЭК в контакт покупателя")

    # --- Доп. услуги / оплата ---
    declared_value: float = Field(default=0, ge=0, description="Объявленная стоимость, ₽ (база страхования)")
    insurance: bool = Field(default=False, description="Страхование по объявленной стоимости")
    sms: bool = Field(default=False, description="СМС-уведомление получателю")
    cod_amount: float = Field(default=0, ge=0, description="Наложенный платёж, ₽ (получатель платит за товар)")
    delivery_paid_by_recipient: bool = Field(default=False, description="Доставку оплачивает получатель")
    delivery_cost: float = Field(default=0, ge=0, description="Сумма доставки (тариф), если платит получатель")
