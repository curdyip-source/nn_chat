"""«Поиск по приёмкам» в приложении: цена товара по нашим приёмкам.

Отбор — как в точном поиске по прайсам (price_federation.proxy_search_all, strict):
каждое слово запроса должно встречаться в наименовании или артикуле позиции.
Позиции одного товара (по product_id, иначе по наименованию) в одной валюте
сворачиваются в одну строку, цена — по выбранному режиму:

- ``last``    — цена из последней приёмки с этим товаром;
- ``avg_all`` — средняя за всё время;
- ``avg_3m``  — средняя за последние 3 месяца (90 дней).

Средняя — по приёмкам, а не по штукам: каждая позиция приёмки считается один раз.
Видимость — как у списка приёмок (склады пользователя, см. list_visibility).
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_, false, func, or_
from sqlalchemy.orm import Session

from app.models.product_registrations import ProductRegistration, ProductRegistrationItem
from app.models.reference_data import Currency
from app.services.access_control import list_visibility

MODES = ("last", "avg_all", "avg_3m")
_THREE_MONTHS = timedelta(days=90)
# Сколько позиций приёмок максимум сворачиваем за один запрос — с запасом на любые
# реальные объёмы; дальше строки старые и на «последнюю» цену не влияют.
_SCAN_LIMIT = 5000


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_registration_prices(db: Session, current_user: dict, query: str, mode: str, limit: int = 50) -> dict:
    if mode not in MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный режим цены")
    tokens = [t for t in (query or "").lower().split() if t]
    if not tokens:
        return {"count": 0, "results": []}

    haystack = func.lower(
        ProductRegistrationItem.product_registration_item_name
        + " "
        + func.coalesce(ProductRegistrationItem.product_registration_item_article, "")
    )
    q = (
        db.query(ProductRegistrationItem, ProductRegistration, Currency)
        .join(ProductRegistration, ProductRegistration.product_registration_id == ProductRegistrationItem.product_registration_item_product_registration_id)
        .outerjoin(Currency, Currency.currency_id == ProductRegistrationItem.product_registration_item_currency_id)
    )
    for token in tokens:
        q = q.filter(haystack.like(f"%{_escape_like(token)}%", escape="\\"))

    # Видимость per-warehouse — та же, что у списка приёмок.
    full_ids, own_ids, user_id = list_visibility(db, current_user)
    if full_ids is not None:
        conditions = []
        if full_ids:
            conditions.append(ProductRegistration.product_registration_establishment_id.in_(full_ids))
        if own_ids:
            conditions.append(and_(ProductRegistration.product_registration_establishment_id.in_(own_ids), ProductRegistration.product_registration_owner_user_id == user_id))
        q = q.filter(or_(*conditions) if conditions else false())

    if mode == "avg_3m":
        q = q.filter(ProductRegistration.product_registration_created_at >= datetime.utcnow() - _THREE_MONTHS)

    rows = (
        q.order_by(ProductRegistration.product_registration_created_at.desc(), ProductRegistration.product_registration_id.desc())
        .limit(_SCAN_LIMIT)
        .all()
    )

    # Строки идут от новых к старым: первая встреченная по ключу — последняя приёмка.
    groups: dict[tuple, dict] = {}
    for item, registration, currency in rows:
        product_key = item.product_registration_item_product_id or item.product_registration_item_name.strip().lower()
        key = (product_key, item.product_registration_item_currency_id)
        group = groups.get(key)
        if group is None:
            group = groups[key] = {
                "name": item.product_registration_item_name,
                "code": item.product_registration_item_article,
                "last_cost": item.product_registration_item_cost,
                "last_registration_id": registration.product_registration_id,
                "last_date": registration.product_registration_created_at,
                "currency": (currency.currency_sign or currency.currency_name) if currency else None,
                "currency_name": currency.currency_name if currency else None,
                "costs": [],
            }
        group["costs"].append(Decimal(item.product_registration_item_cost))

    results = []
    for (product_key, currency_id), group in groups.items():
        if mode == "last":
            price = Decimal(group["last_cost"])
        else:
            price = sum(group["costs"], Decimal("0")) / len(group["costs"])
        results.append({
            "id": f"{product_key}-{currency_id}",
            "name": group["name"],
            "code": group["code"],
            "price": str(price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "currency": group["currency"],
            # Цены прайсов — в USD, их показываем без знака; знак нужен только для прочих валют.
            "is_default_currency": group["currency_name"] in (None, "USD"),
            "registration_id": group["last_registration_id"],
            "registrations_count": len(group["costs"]),
            "last_date": group["last_date"].isoformat() if group["last_date"] else None,
        })

    # Сначала свежие товары — как «последняя приёмка» сверху.
    results.sort(key=lambda r: r["last_date"] or "", reverse=True)
    results = results[:limit]
    return {"count": len(results), "results": results}
