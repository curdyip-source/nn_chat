from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.cdek import CdekWaybillCreate
from app.services import cdek, cdek_orders

router = APIRouter(prefix="/cdek", tags=["cdek"])


def _guard():
    if not cdek.config.CDEK_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Интеграция СДЭК не настроена")


@router.get("/cities/suggest")
def suggest_cities_route(
    name: str = Query(min_length=2, max_length=100),
    _: dict = Depends(get_current_user),
) -> dict:
    """Поиск города по названию (автодополнение) — пользователь видит имена, не коды."""
    _guard()
    try:
        return {"items": cdek.suggest_cities(name)}
    except cdek.CdekError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get("/delivery-points")
def delivery_points_route(
    city_code: int = Query(ge=1),
    query: str | None = Query(default=None, max_length=200),
    type: str = Query(default="PVZ"),
    _: dict = Depends(get_current_user),
) -> dict:
    """ПВЗ/постаматы выбранного города; при `query` фильтруем по адресу/названию."""
    _guard()
    try:
        points = cdek.delivery_points(city_code, type_=type)
    except cdek.CdekError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if query:
        q = query.strip().lower()
        points = [p for p in points if q in (p["address"] or "").lower() or q in (p["name"] or "").lower()]
    return {"items": points}


@router.get("/tariffs")
def tariffs_route(
    to_code: int = Query(ge=1),
    from_code: int | None = Query(default=None, ge=1),
    weight: int = Query(default=500, ge=1),
    _: dict = Depends(get_current_user),
) -> dict:
    """Доступные тарифы (цены/сроки). from_code по умолчанию — город отправителя (конфиг)."""
    _guard()
    sender = from_code or cdek.config.CDEK_SENDER_CITY_CODE
    try:
        return {"items": cdek.calculate_tariff_list(sender, to_code, weight)}
    except cdek.CdekError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post("/orders/{order_id}/waybill", status_code=status.HTTP_201_CREATED)
def create_waybill_route(
    order_id: int,
    payload: CdekWaybillCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Создать накладную СДЭК для заказа (сохраняет uuid/трек/статус в заказ)."""
    return {"item": cdek_orders.create_waybill(db, order_id, payload, current_user)}


@router.get("/orders/{order_id}/status")
def waybill_status_route(
    order_id: int,
    _: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Актуальный статус накладной СДЭК заказа (подтягивает из CDEK)."""
    return {"item": cdek_orders.get_status(db, order_id)}
