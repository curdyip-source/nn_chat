"""Прокси к прайс-бэкенду (nn_vla): живой поиск по прайс-листам + список источников.

Приложению/вебу не нужно ходить в nn_vla напрямую — chat-бэкенд проксирует запрос
своим сервисным токеном (nn_vla доверяет тому же AUTH_TOKEN_SECRET). Так поиск
работает по всем прайс-листам (не по CL-зеркалу в нашей БД).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user
from app.services.price_federation import proxy_search_all, proxy_suppliers

router = APIRouter(tags=["price"])


@router.get("/price/suppliers")
def price_suppliers_route(_: dict = Depends(get_current_user)) -> dict:
    try:
        return {"items": proxy_suppliers()}
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Прайс недоступен")


@router.get("/price/search")
def price_search_route(
    q: str = Query(default=""),
    emails: list[str] = Query(default=[], description="Источники: CL и/или email; пусто = все"),
    limit: int = Query(default=50, ge=1, le=200),
    _: dict = Depends(get_current_user),
) -> dict:
    try:
        return proxy_search_all(q, emails or None, limit)
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Прайс недоступен")
