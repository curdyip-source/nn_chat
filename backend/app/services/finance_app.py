"""«Финансы» в приложении — упрощённый вариант веб-раздела: отгруженные позиции за
период, внесение закупочной цены и «фиксатор».

Упрощение относительно веба: всё считается В ВАЛЮТЕ ПРОДАЖИ, без пересчёта в рубли
по курсу. Выручка и прибыль — суммы по каждой валюте отдельно. Закупочная цена
вносится в той же валюте, что и продажа (order_item_purchase_price); параллельно
пересчитывается order_item_cost_usd, чтобы веб-«Финансы» видели те же цифры.

«Отгружено» — как и в вебе: по order_item_shipped_at (момент перехода позиции в
«Отгружено»), а не по дате создания заказа.
"""

from collections import OrderedDict
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.orders import Order, OrderItem
from app.services.exchange_rates import get_rate_for_date
from app.services.serializers import serialize_datetime

_CENT = Decimal("0.01")


def _currency_name(item: OrderItem) -> str:
    currency = getattr(item, "currency", None)
    return ((currency.currency_name if currency else None) or "RUB").strip().upper()


def _currency_label(item: OrderItem) -> str:
    currency = getattr(item, "currency", None)
    if currency is None:
        return "₽"
    return currency.currency_sign or currency.currency_name


def _suggested_purchase(item: OrderItem) -> Decimal | None:
    """Подсказка для поля закупки — снимок себестоимости из каталога в валюте продажи.
    Это НЕ внесённая закупка (снимок бывает неверным), только плейсхолдер."""
    if item.order_item_cost_usd is None:
        return None
    if _currency_name(item) == "USD":
        return Decimal(item.order_item_cost_usd)
    if item.order_item_cost_rate is None:
        return None
    return (Decimal(item.order_item_cost_usd) * Decimal(item.order_item_cost_rate)).quantize(_CENT, rounding=ROUND_HALF_UP)


def sync_cost_usd_from_purchase(db: Session, item: OrderItem) -> None:
    """Пересчитать order_item_cost_usd из закупки в валюте продажи (для веба).
    Для не-USD нужен курс: снимок позиции, иначе курс на дату отгрузки (и он же
    сохраняется в позицию). Нет курса — cost_usd не трогаем, веб пометит позицию."""
    purchase = item.order_item_purchase_price
    if purchase is None:
        return
    if _currency_name(item) == "USD":
        item.order_item_cost_usd = Decimal(purchase)
        return
    rate = item.order_item_cost_rate
    if rate is None:
        target = (item.order_item_shipped_at or datetime.utcnow()).date()
        rate_row = get_rate_for_date(db, target)
        if rate_row is None:
            return
        rate = rate_row.exchange_rate_value
        item.order_item_cost_rate = rate
    item.order_item_cost_usd = (Decimal(purchase) / Decimal(rate)).quantize(_CENT, rounding=ROUND_HALF_UP)


def purchase_from_cost_usd(item: OrderItem) -> Decimal | None:
    """Обратная связь: веб правит cost_usd/курс — закупка в валюте продажи следом."""
    if item.order_item_cost_usd is None:
        return None
    if _currency_name(item) == "USD":
        return Decimal(item.order_item_cost_usd)
    if item.order_item_cost_rate is None:
        return None
    return (Decimal(item.order_item_cost_usd) * Decimal(item.order_item_cost_rate)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _serialize(item: OrderItem) -> dict:
    order = item.order
    establishment = getattr(order, "establishment", None) if order else None
    suggested = _suggested_purchase(item)
    return {
        "order_item_id": item.order_item_id,
        "order_id": item.order_item_order_id,
        "shipped_at": serialize_datetime(item.order_item_shipped_at),
        # День отгрузки — в той же шкале, что и фильтр периода (UTC-дата), чтобы
        # строка не «переезжала» в соседний день относительно фильтра.
        "shipped_date": item.order_item_shipped_at.date().isoformat() if item.order_item_shipped_at else None,
        "establishment_name": establishment.establishment_name if establishment else None,
        "name": item.order_item_name,
        "article": item.order_item_article,
        "quantity": item.order_item_quantity,
        "price": format(Decimal(item.order_item_price), "f"),
        "currency": _currency_label(item),
        "purchase_price": format(Decimal(item.order_item_purchase_price), "f") if item.order_item_purchase_price is not None else None,
        "suggested_purchase_price": format(suggested, "f") if suggested is not None else None,
        "locked": bool(item.order_item_cost_locked),
    }


def _get_item_or_404(db: Session, order_item_id: int) -> OrderItem:
    item = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.currency), joinedload(OrderItem.order).joinedload(Order.establishment))
        .filter(OrderItem.order_item_id == order_item_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция заказа не найдена")
    return item


def list_app_finance(db: Session, date_from: date, date_to: date) -> dict:
    if date_to < date_from:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="«Дата до» не может быть раньше «даты от»")
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to + timedelta(days=1), time.min)
    items = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.currency), joinedload(OrderItem.order).joinedload(Order.establishment))
        .filter(OrderItem.order_item_shipped_at.isnot(None))
        .filter(OrderItem.order_item_shipped_at >= start, OrderItem.order_item_shipped_at < end)
        .order_by(OrderItem.order_item_shipped_at.desc(), OrderItem.order_item_id.desc())
        .all()
    )

    # Суммы по валютам в порядке первого появления. Прибыль — только по позициям
    # с внесённой закупкой (без неё прибыль неизвестна, а не равна выручке).
    revenue: "OrderedDict[str, Decimal]" = OrderedDict()
    profit: "OrderedDict[str, Decimal]" = OrderedDict()
    missing = 0
    for item in items:
        label = _currency_label(item)
        quantity = Decimal(item.order_item_quantity)
        revenue[label] = revenue.get(label, Decimal("0")) + Decimal(item.order_item_price) * quantity
        if item.order_item_purchase_price is None:
            missing += 1
            continue
        profit[label] = profit.get(label, Decimal("0")) + (Decimal(item.order_item_price) - Decimal(item.order_item_purchase_price)) * quantity

    def totals(values: "OrderedDict[str, Decimal]") -> list[dict]:
        return [{"currency": currency, "amount": format(amount.quantize(_CENT), "f")} for currency, amount in values.items()]

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "revenue": totals(revenue),
        "profit": totals(profit),
        "items_count": len(items),
        "missing_purchase_count": missing,
        "items": [_serialize(item) for item in items],
    }


def set_purchase_price(db: Session, order_item_id: int, purchase_price: Decimal | None, current_user: dict) -> dict:
    item = _get_item_or_404(db, order_item_id)
    if item.order_item_cost_locked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Позиция зафиксирована — снимите фиксатор, чтобы изменить закупку")
    item.order_item_purchase_price = purchase_price
    sync_cost_usd_from_purchase(db, item)
    item.order_item_cost_updated_at = datetime.utcnow()
    item.order_item_cost_updated_by_user_id = current_user["user_id"]
    db.commit()
    return _serialize(_get_item_or_404(db, order_item_id))


def set_locked(db: Session, order_item_id: int, locked: bool, current_user: dict) -> dict:
    item = _get_item_or_404(db, order_item_id)
    if locked and item.order_item_purchase_price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сначала внесите закупочную цену")
    item.order_item_cost_locked = locked
    item.order_item_cost_locked_at = datetime.utcnow() if locked else None
    item.order_item_cost_locked_by_user_id = current_user["user_id"] if locked else None
    db.commit()
    return _serialize(_get_item_or_404(db, order_item_id))
