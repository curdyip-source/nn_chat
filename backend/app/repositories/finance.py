from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.finance import ExchangeRate, FinanceExpense, FinanceExpenseCategory
from app.models.orders import Order, OrderItem
from app.models.reference_data import Status

# Товар считается «проданным» для финансового свода, когда позиция реально уехала —
# это статус позиции (order_products), а не статус всего заказа: в одном заказе
# позиции едут независимо (для этого и есть его разделение на «готово»/«остальное»).
SOLD_ITEM_STATUS_TYPE = "order_products"
SOLD_ITEM_STATUS_NAME = "Отгружено"


class ExchangeRateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_range(self, date_from: date, date_to: date) -> list[ExchangeRate]:
        return (
            self.db.query(ExchangeRate)
            .filter(ExchangeRate.exchange_rate_date >= date_from, ExchangeRate.exchange_rate_date <= date_to)
            .order_by(ExchangeRate.exchange_rate_date.desc())
            .all()
        )

    def get_by_date(self, target_date: date) -> ExchangeRate | None:
        return self.db.query(ExchangeRate).filter(ExchangeRate.exchange_rate_date == target_date).first()

    def upsert_manual(self, target_date: date, value, current_user_id: int) -> ExchangeRate:
        row = self.get_by_date(target_date)
        if row is None:
            row = ExchangeRate(exchange_rate_date=target_date, exchange_rate_value=value, exchange_rate_source="manual")
            self.db.add(row)
        else:
            row.exchange_rate_value = value
            row.exchange_rate_source = "manual"
        row.exchange_rate_updated_by_user_id = current_user_id
        self.db.commit()
        self.db.refresh(row)
        return row


class FinanceExpenseCategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[FinanceExpenseCategory]:
        return (
            self.db.query(FinanceExpenseCategory)
            .options(joinedload(FinanceExpenseCategory.owner))
            .order_by(FinanceExpenseCategory.finance_expense_category_name.asc())
            .all()
        )

    def get(self, category_id: int) -> FinanceExpenseCategory | None:
        return (
            self.db.query(FinanceExpenseCategory)
            .options(joinedload(FinanceExpenseCategory.owner))
            .filter(FinanceExpenseCategory.finance_expense_category_id == category_id)
            .first()
        )

    def create(self, data: dict) -> FinanceExpenseCategory:
        row = FinanceExpenseCategory(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get(row.finance_expense_category_id)

    def update(self, row: FinanceExpenseCategory, data: dict) -> FinanceExpenseCategory:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get(row.finance_expense_category_id)


class FinanceExpenseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, expense_id: int) -> FinanceExpense | None:
        return (
            self.db.query(FinanceExpense)
            .options(joinedload(FinanceExpense.category), joinedload(FinanceExpense.owner))
            .filter(FinanceExpense.finance_expense_id == expense_id)
            .first()
        )

    def list_for_range(self, date_from: date, date_to: date) -> list[FinanceExpense]:
        # Точное сравнение по дате — как фильтр в «Заказах» (не обрезаем до месяца).
        return (
            self.db.query(FinanceExpense)
            .options(joinedload(FinanceExpense.category), joinedload(FinanceExpense.owner))
            .filter(FinanceExpense.finance_expense_period >= date_from, FinanceExpense.finance_expense_period <= date_to)
            .order_by(FinanceExpense.finance_expense_created_at.desc())
            .all()
        )

    def sum_for_range(self, date_from: date, date_to: date) -> Decimal:
        total = (
            self.db.query(func.coalesce(func.sum(FinanceExpense.finance_expense_amount), 0))
            .filter(FinanceExpense.finance_expense_period >= date_from, FinanceExpense.finance_expense_period <= date_to)
            .scalar()
        )
        return Decimal(total or 0)

    def create(self, data: dict) -> FinanceExpense:
        row = FinanceExpense(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get(row.finance_expense_id)

    def update(self, row: FinanceExpense, data: dict) -> FinanceExpense:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get(row.finance_expense_id)

    def delete(self, row: FinanceExpense) -> None:
        self.db.delete(row)
        self.db.commit()


class FinanceOrderItemRepository:
    """Заказы/позиции за диапазон дат для свода П/У (выручка, себестоимость, ревью без цены)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_items_for_range(self, date_from: date, date_to: date) -> list[OrderItem]:
        # Диапазон — по дате СОЗДАНИЯ заказа (своей даты отгрузки позиция не хранит),
        # как и фильтр по датам в разделе «Заказы» (OrderRepository._apply_order_filters).
        # date_to включительно — берём весь день до полуночи следующего.
        start = datetime.combine(date_from, time.min)
        end = datetime.combine(date_to + timedelta(days=1), time.min)
        return (
            self.db.query(OrderItem)
            .join(Order, OrderItem.order_item_order_id == Order.order_id)
            .join(Status, OrderItem.order_item_status_id == Status.status_id)
            .options(joinedload(OrderItem.order), joinedload(OrderItem.currency))
            .filter(Order.order_created_at >= start, Order.order_created_at < end)
            .filter(Status.status_type == SOLD_ITEM_STATUS_TYPE, Status.status_status == SOLD_ITEM_STATUS_NAME)
            .order_by(OrderItem.order_item_created_at.desc(), OrderItem.order_item_id.desc())
            .all()
        )

    def get_item(self, order_item_id: int) -> OrderItem | None:
        return self.db.query(OrderItem).options(joinedload(OrderItem.currency)).filter(OrderItem.order_item_id == order_item_id).first()
