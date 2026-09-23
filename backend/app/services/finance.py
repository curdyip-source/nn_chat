from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.finance import (
    ExchangeRateRepository,
    FinanceExpenseCategoryRepository,
    FinanceExpenseRepository,
    FinanceOrderItemRepository,
)
from app.schemas.common import build_pagination, model_to_dict
from app.schemas.finance import (
    BulkOrderItemCostRatePayload,
    ExchangeRateOverridePayload,
    FinanceExpenseCategoryPayload,
    FinanceExpensePayload,
    OrderItemCostCorrectionPayload,
)
from app.services.serializers import (
    compute_order_item_money,
    serialize_exchange_rate,
    serialize_finance_expense,
    serialize_finance_expense_category,
    serialize_order_item,
)


def _parse_expense_date(value: str | date) -> date:
    """Точная дата расхода (не обрезаем до 1-го числа!) — иначе фильтр по диапазону
    дат внутри одного месяца ничего не мог бы отсеять, т.к. день терялся бы при
    сохранении. Строка вида YYYY-MM (без дня) достраивается до 1-го числа."""
    if isinstance(value, date):
        return value
    text = value.strip()
    try:
        return date.fromisoformat(text if len(text) > 7 else f"{text}-01")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Некорректная дата, ожидается YYYY-MM-DD") from exc


class FinanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rates = ExchangeRateRepository(db)
        self.categories = FinanceExpenseCategoryRepository(db)
        self.expenses = FinanceExpenseRepository(db)
        self.order_items = FinanceOrderItemRepository(db)

    # --- Курс ---

    def list_exchange_rates(self, date_from: date, date_to: date) -> dict:
        return {"items": [serialize_exchange_rate(row) for row in self.rates.list_range(date_from, date_to)]}

    def override_exchange_rate(self, target_date: date, payload: ExchangeRateOverridePayload, current_user: dict) -> dict:
        row = self.rates.upsert_manual(target_date, payload.exchange_rate_value, current_user["user_id"])
        return serialize_exchange_rate(row)

    # --- Категории расходов ---

    def list_expense_categories(self) -> dict:
        return {"items": [serialize_finance_expense_category(row) for row in self.categories.list()]}

    def create_expense_category(self, payload: FinanceExpenseCategoryPayload, current_user: dict) -> dict:
        row = self.categories.create({**model_to_dict(payload), "finance_expense_category_owner_user_id": current_user["user_id"]})
        return serialize_finance_expense_category(row)

    def update_expense_category(self, category_id: int, payload: FinanceExpenseCategoryPayload) -> dict:
        row = self.categories.get(category_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория расходов не найдена")
        return serialize_finance_expense_category(self.categories.update(row, model_to_dict(payload)))

    # --- Расходы (без блокировки по месяцу — это просто фильтр по дате) ---

    def list_expenses(self, date_from: date, date_to: date) -> dict:
        return {"items": [serialize_finance_expense(row) for row in self.expenses.list_for_range(date_from, date_to)]}

    def create_expense(self, payload: FinanceExpensePayload, current_user: dict) -> dict:
        data = model_to_dict(payload)
        data["finance_expense_period"] = _parse_expense_date(payload.finance_expense_period)
        data["finance_expense_owner_user_id"] = current_user["user_id"]
        row = self.expenses.create(data)
        return serialize_finance_expense(row)

    def update_expense(self, expense_id: int, payload: FinanceExpensePayload) -> dict:
        row = self.expenses.get(expense_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расход не найден")
        data = model_to_dict(payload)
        data["finance_expense_period"] = _parse_expense_date(payload.finance_expense_period)
        return serialize_finance_expense(self.expenses.update(row, data))

    def delete_expense(self, expense_id: int) -> None:
        row = self.expenses.get(expense_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расход не найден")
        self.expenses.delete(row)

    # --- Себестоимость позиции ---

    def correct_order_item_cost(self, order_item_id: int, payload: OrderItemCostCorrectionPayload, current_user: dict) -> dict:
        row = self.order_items.get_item(order_item_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция заказа не найдена")
        row.order_item_cost_usd = payload.order_item_cost_usd
        row.order_item_cost_rate = payload.order_item_cost_rate
        row.order_item_cost_updated_at = datetime.utcnow()
        row.order_item_cost_updated_by_user_id = current_user["user_id"]
        self.db.commit()
        self.db.refresh(row)
        return serialize_order_item(row)

    def bulk_set_cost_rate(self, order_item_ids: list[int], rate, current_user: dict) -> dict:
        # Массовая правка курса для отмеченных галочками позиций (напр. когда снимок
        # курса не попал в дату — проставляем один и тот же исторический курс сразу
        # на пачку). Себестоимость в USD не трогаем — только курс.
        updated_ids: list[int] = []
        not_found_ids: list[int] = []
        now = datetime.utcnow()
        for order_item_id in order_item_ids:
            row = self.order_items.get_item(order_item_id)
            if row is None:
                not_found_ids.append(order_item_id)
                continue
            row.order_item_cost_rate = rate
            row.order_item_cost_updated_at = now
            row.order_item_cost_updated_by_user_id = current_user["user_id"]
            updated_ids.append(order_item_id)
        self.db.commit()
        return {"updated_ids": updated_ids, "not_found_ids": not_found_ids}

    # --- Свод за диапазон дат (как фильтр в «Заказах» — дата от/до, без закрытия) ---

    def get_summary(self, date_from: date, date_to: date, *, page: int = 1, page_size: int = 100) -> dict:
        # items уже отфильтрован репозиторием до статуса позиции «Отгружено» — это и есть
        # «продано» для свода (отменённые/возвраты/ещё не собранные сюда не попадают), и
        # отсортирован новыми сверху.
        #
        # compute_order_item_money конвертирует цену/себестоимость в рубли по курсу на
        # дату заказа — цена хранится В ВАЛЮТЕ ПОЗИЦИИ (по умолчанию USD, не рубли!).
        # Если курса нет — не примешиваем половинчатые цифры ни к выручке, ни к
        # себестоимости, а просто помечаем позицию на ревью.
        if date_to < date_from:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="«Дата до» не может быть раньше «даты от»")

        items = self.order_items.list_items_for_range(date_from, date_to)

        revenue = Decimal("0")
        cost_rub = Decimal("0")
        missing_cost_count = 0
        serialized_items = []
        for item in items:
            money = compute_order_item_money(item)
            resolved = money["price_rub"] is not None and money["cost_rub"] is not None
            if resolved:
                revenue += money["price_rub"] * item.order_item_quantity
                cost_rub += money["cost_rub"] * item.order_item_quantity
            else:
                missing_cost_count += 1
            serialized_items.append(serialize_order_item(item))

        # Расходы заведены по месяцам — считаем любой месяц, задетый диапазоном хотя бы частично.
        expenses_total = self.expenses.sum_for_range(date_from, date_to)
        gross_profit = revenue - cost_rub
        net_profit = gross_profit - expenses_total

        total_items = len(serialized_items)
        page_items = serialized_items[(page - 1) * page_size : (page - 1) * page_size + page_size]

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "revenue": str(revenue),
            "cost_rub": str(cost_rub),
            "gross_profit": str(gross_profit),
            "expenses_total": str(expenses_total),
            "net_profit": str(net_profit),
            "items_count": total_items,
            "missing_cost_count": missing_cost_count,
            "items": page_items,
            "pagination": build_pagination(page, page_size, total_items),
            "expenses": [serialize_finance_expense(row) for row in self.expenses.list_for_range(date_from, date_to)],
        }


def list_exchange_rates(db: Session, date_from: date, date_to: date) -> dict:
    return FinanceService(db).list_exchange_rates(date_from, date_to)


def override_exchange_rate(db: Session, target_date: date, payload: ExchangeRateOverridePayload, current_user: dict) -> dict:
    return FinanceService(db).override_exchange_rate(target_date, payload, current_user)


def list_expense_categories(db: Session) -> dict:
    return FinanceService(db).list_expense_categories()


def create_expense_category(db: Session, payload: FinanceExpenseCategoryPayload, current_user: dict) -> dict:
    return FinanceService(db).create_expense_category(payload, current_user)


def update_expense_category(db: Session, category_id: int, payload: FinanceExpenseCategoryPayload) -> dict:
    return FinanceService(db).update_expense_category(category_id, payload)


def list_expenses(db: Session, date_from: date, date_to: date) -> dict:
    return FinanceService(db).list_expenses(date_from, date_to)


def create_expense(db: Session, payload: FinanceExpensePayload, current_user: dict) -> dict:
    return FinanceService(db).create_expense(payload, current_user)


def update_expense(db: Session, expense_id: int, payload: FinanceExpensePayload) -> dict:
    return FinanceService(db).update_expense(expense_id, payload)


def delete_expense(db: Session, expense_id: int) -> None:
    FinanceService(db).delete_expense(expense_id)


def correct_order_item_cost(db: Session, order_item_id: int, payload: OrderItemCostCorrectionPayload, current_user: dict) -> dict:
    return FinanceService(db).correct_order_item_cost(order_item_id, payload, current_user)


def bulk_set_order_item_cost_rate(db: Session, payload: BulkOrderItemCostRatePayload, current_user: dict) -> dict:
    return FinanceService(db).bulk_set_cost_rate(payload.order_item_ids, payload.order_item_cost_rate, current_user)


def get_summary(db: Session, date_from: date, date_to: date, *, page: int = 1, page_size: int = 100) -> dict:
    return FinanceService(db).get_summary(date_from, date_to, page=page, page_size=page_size)
