"""Прокси к прайс-бэкенду (nn_vla): живой поиск по прайс-листам + список источников.

Приложению/вебу не нужно ходить в nn_vla напрямую — chat-бэкенд проксирует запрос
своим сервисным токеном (nn_vla доверяет тому же AUTH_TOKEN_SECRET). Так поиск
работает по всем прайс-листам (не по CL-зеркалу в нашей БД).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_section
from app.services.price_federation import proxy_search_all, proxy_suppliers
from app.services.registration_price_search import search_registration_prices

router = APIRouter(tags=["price"])

# Режим приложения «Поиск по прайсу» (ключ price). Веб-раздел «Прайс» — отдельный
# ключ web_price, его проверяет сам бэкенд прайса.
require_price_search = require_section("price")


@router.get("/price/suppliers")
def price_suppliers_route(_: dict = Depends(require_price_search)) -> dict:
    try:
        return {"items": proxy_suppliers()}
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Прайс недоступен")


@router.get("/price/search")
def price_search_route(
    q: str = Query(default=""),
    emails: list[str] = Query(default=[], description="Источники: CL и/или email; пусто = все"),
    limit: int = Query(default=50, ge=1, le=200),
    strict: bool = Query(default=False, description="Точный режим: все токены запроса в наименовании"),
    _: dict = Depends(require_price_search),
) -> dict:
    try:
        return proxy_search_all(q, emails or None, limit, strict=strict)
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Прайс недоступен")


@router.get("/price/registrations")
def price_registrations_route(
    q: str = Query(default=""),
    mode: str = Query(default="last", description="last — последняя приёмка; avg_all — средняя за всё время; avg_3m — средняя за 3 месяца"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_price_search),
    db: Session = Depends(get_db),
) -> dict:
    # «Поиск по приёмкам»: цены из наших приёмок, отбор как у точного поиска по прайсам.
    return search_registration_prices(db, current_user, q, mode, limit)
