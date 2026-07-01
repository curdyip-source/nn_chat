"""Федерация каталога товаров со свежим прайсом nn_vla (источник правды CL).

Локальная таблица ``products`` перестаёт быть большим постоянным каталогом: при
поиске/сопоставлении бэкенд спрашивает свежий CL у nn_vla и лениво до-заносит
найденное в ``products`` по артикулу (с обновлением цены). Так iOS/веб-клиенты
работают без изменений (у товара есть реальный локальный ``product_id``), а
каталог держит только реально используемые позиции, освежаемые из nn_vla.

Мягкий фолбэк: любая ошибка обращения к nn_vla логируется и НЕ ломает локальный
поиск — просто вернём 0 гидратированных строк.
"""

import logging
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import PRICE_BACKEND_URL, PRICE_FEDERATION_USER_ID
from app.core.tokens import create_access_token
from app.models.reference_data import Product

logger = logging.getLogger("app.price_federation")

_HTTP_TIMEOUT = httpx.Timeout(4.0)
_FETCH_LIMIT = 100


def _service_token() -> str:
    token, _ = create_access_token(session_id=0, user_id=PRICE_FEDERATION_USER_ID)
    return token


def _to_cost(value) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _fetch_cl_rows(query: str) -> list[dict]:
    """Свежие строки CL из nn_vla по запросу. [] при любой ошибке/выключенной федерации."""
    q = (query or "").strip()
    if not q or not PRICE_BACKEND_URL:
        return []
    try:
        response = httpx.get(
            f"{PRICE_BACKEND_URL}/api/search/all",
            params={"q": q, "limit": _FETCH_LIMIT, "emails": ["CL"]},
            headers={"Authorization": f"Bearer {_service_token()}"},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception:  # noqa: BLE001 — федерация не должна ронять локальный поиск
        logger.warning(
            "price_federation.fetch_failed",
            extra={"event_type": "price_federation.fetch_failed", "query": q},
        )
        return []
    return [r for r in results if isinstance(r, dict) and r.get("source") == "CL"]


def hydrate_products(db: Session, *, query: str) -> int:
    """Спросить nn_vla по ``query`` и апсертнуть строки CL в ``products`` по артикулу.

    Возвращает число присланных строк (0 при недоступности nn_vla). Апсерт — один
    stmt (INSERT .. ON CONFLICT (product_article) DO UPDATE name/cost), ничего не
    удаляет: ручные позиции и прочие товары не трогаются.
    """
    rows = _fetch_cl_rows(query)
    if not rows:
        return 0

    values: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        if not code or not name or code in seen:
            continue
        seen.add(code)
        values.append(
            {
                "product_article": code[:100],
                "product_name": name[:500],
                "product_cost_usd": _to_cost(row.get("price")),
                "product_owner_user_id": None,
            }
        )

    if not values:
        return 0

    stmt = pg_insert(Product).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Product.product_article],
        set_={
            "product_name": stmt.excluded.product_name,
            "product_cost_usd": stmt.excluded.product_cost_usd,
        },
    )
    try:
        db.execute(stmt)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "price_federation.upsert_failed",
            extra={"event_type": "price_federation.upsert_failed", "query": query, "count": len(values)},
        )
        return 0

    logger.info(
        "price_federation.hydrated",
        extra={"event_type": "price_federation.hydrated", "query": query, "count": len(values)},
    )
    return len(values)


def hydrate_products_for_names(db: Session, names: list[str], *, max_names: int = 100) -> None:
    """Гидратация под список наименований (импорт документа в заказ): по каждому
    имени спрашиваем nn_vla, чтобы последующий матч по имени нашёл свежие позиции."""
    seen: set[str] = set()
    for raw in names[:max_names]:
        name = (raw or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        hydrate_products(db, query=name)
