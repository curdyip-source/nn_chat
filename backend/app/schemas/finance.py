from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ExchangeRateOverridePayload(BaseModel):
    exchange_rate_value: Decimal = Field(gt=0, decimal_places=4, max_digits=10)


class FinanceExpenseCategoryPayload(BaseModel):
    finance_expense_category_name: str = Field(min_length=1, max_length=255)


class FinanceExpensePayload(BaseModel):
    finance_expense_category_id: int
    # Точная дата расхода (не обрезается до месяца) — фильтр по диапазону работает
    # день в день, как в «Заказах».
    finance_expense_period: str = Field(description="YYYY-MM-DD")
    finance_expense_amount: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    finance_expense_note: Optional[str] = Field(default=None, max_length=500)


class OrderItemCostCorrectionPayload(BaseModel):
    order_item_cost_usd: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    order_item_cost_rate: Optional[Decimal] = Field(default=None, gt=0, decimal_places=4, max_digits=10)


class BulkOrderItemCostRatePayload(BaseModel):
    order_item_ids: list[int] = Field(min_length=1, max_length=500)
    order_item_cost_rate: Decimal = Field(gt=0, decimal_places=4, max_digits=10)
