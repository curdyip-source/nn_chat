from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_section
from app.schemas.finance import (
    BulkOrderItemCostRatePayload,
    ExchangeRateOverridePayload,
    FinanceExpenseCategoryPayload,
    FinanceExpensePayload,
    OrderItemCostCorrectionPayload,
)
from app.services.finance import (
    bulk_set_order_item_cost_rate,
    correct_order_item_cost,
    create_expense,
    create_expense_category,
    delete_expense,
    get_summary,
    list_exchange_rates,
    list_expense_categories,
    list_expenses,
    override_exchange_rate,
    update_expense,
    update_expense_category,
)

# Раздел «Финансы» — как остальные разделы СРМ веба (orders/products/...): доступен
# админам всегда, остальным — если выдан в user_sections (крм + finance), см.
# «Разделы СРМ (веб)» в правах пользователя.
router = APIRouter(prefix="/finance", tags=["finance"])
require_finance = require_section("crm", "finance")


@router.get("/exchange-rates")
def get_exchange_rates(
    _: dict = Depends(require_finance),
    db: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict:
    resolved_to = date_to or date.today()
    resolved_from = date_from or (resolved_to - timedelta(days=30))
    return list_exchange_rates(db, resolved_from, resolved_to)


@router.put("/exchange-rates/{rate_date}")
def override_exchange_rate_route(
    rate_date: date,
    payload: ExchangeRateOverridePayload,
    current_user: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": override_exchange_rate(db, rate_date, payload, current_user)}


@router.get("/expense-categories")
def get_expense_categories(_: dict = Depends(require_finance), db: Session = Depends(get_db)) -> dict:
    return list_expense_categories(db)


@router.post("/expense-categories", status_code=status.HTTP_201_CREATED)
def create_expense_category_route(
    payload: FinanceExpenseCategoryPayload,
    current_user: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": create_expense_category(db, payload, current_user)}


@router.put("/expense-categories/{category_id}")
def update_expense_category_route(
    category_id: int,
    payload: FinanceExpenseCategoryPayload,
    _: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": update_expense_category(db, category_id, payload)}


@router.get("/expenses")
def get_expenses(
    date_from: date = Query(),
    date_to: date = Query(),
    _: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return list_expenses(db, date_from, date_to)


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
def create_expense_route(
    payload: FinanceExpensePayload,
    current_user: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": create_expense(db, payload, current_user)}


@router.put("/expenses/{expense_id}")
def update_expense_route(
    expense_id: int,
    payload: FinanceExpensePayload,
    _: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": update_expense(db, expense_id, payload)}


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_route(expense_id: int, _: dict = Depends(require_finance), db: Session = Depends(get_db)) -> None:
    delete_expense(db, expense_id)


@router.put("/order-items/{order_item_id}/cost")
def correct_order_item_cost_route(
    order_item_id: int,
    payload: OrderItemCostCorrectionPayload,
    current_user: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": correct_order_item_cost(db, order_item_id, payload, current_user)}


@router.put("/order-items/bulk-cost-rate")
def bulk_set_order_item_cost_rate_route(
    payload: BulkOrderItemCostRatePayload,
    current_user: dict = Depends(require_finance),
    db: Session = Depends(get_db),
) -> dict:
    return bulk_set_order_item_cost_rate(db, payload, current_user)


@router.get("/summary")
def get_summary_route(
    date_from: date = Query(),
    date_to: date = Query(),
    _: dict = Depends(require_finance),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> dict:
    return get_summary(db, date_from, date_to, page=page, page_size=page_size)
