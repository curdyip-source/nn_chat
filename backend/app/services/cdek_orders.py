"""Создание накладной СДЭК для заказа и синхронизация статуса.

Собирает тело CDEK /orders из данных заказа + ввода пользователя, создаёт заказ в
СДЭК, сохраняет uuid/трек/статус в колонки order_cdek_*. Печать (2 накладные в чат)
и вебхуки — отдельными шагами.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import config
from app.models.orders import Order
from app.services import cdek


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return order


def _validate(payload) -> None:
    if payload.delivery_mode == "pvz" and not payload.pvz_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для доставки в ПВЗ нужен пункт выдачи")
    if payload.delivery_mode == "door" and not payload.delivery_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для доставки курьером нужен адрес")


def _build_payload(order: Order, payload) -> dict:
    body: dict = {
        "type": 1,
        "tariff_code": payload.tariff_code,
        "sender": {"name": config.CDEK_SENDER_NAME, "phones": [{"number": config.CDEK_SENDER_PHONE}]},
        "from_location": {"code": config.CDEK_SENDER_CITY_CODE, "address": config.CDEK_SENDER_ADDRESS},
        "recipient": {"name": payload.recipient_name, "phones": [{"number": payload.recipient_phone}]},
        "packages": [{
            "number": "1",
            "weight": payload.package.weight,
            "length": payload.package.length,
            "width": payload.package.width,
            "height": payload.package.height,
            "items": [{
                "name": f"Заказ №{order.order_id}",
                "ware_key": str(order.order_id),
                "payment": {"value": 0},
                "cost": 0,
                "weight": payload.package.weight,
                "amount": 1,
            }],
        }],
    }
    if payload.comment:
        body["comment"] = payload.comment
    if payload.delivery_mode == "pvz":
        body["delivery_point"] = payload.pvz_code
    else:
        body["to_location"] = {"code": payload.city_code, "address": payload.delivery_address}
    return body


def _serialize(order: Order) -> dict:
    return {
        "has_waybill": bool(order.order_cdek_uuid),
        "uuid": order.order_cdek_uuid,
        "track_number": order.order_cdek_track_number,
        "status": order.order_cdek_status,
        "status_updated_at": order.order_cdek_status_updated_at.isoformat() if order.order_cdek_status_updated_at else None,
        "recipient_name": order.order_cdek_recipient_name,
        "recipient_phone": order.order_cdek_recipient_phone,
        "city_code": order.order_cdek_city_code,
        "city_name": order.order_cdek_city_name,
        "delivery_mode": order.order_cdek_delivery_mode,
        "pvz_code": order.order_cdek_pvz_code,
        "pvz_address": order.order_cdek_pvz_address,
        "delivery_address": order.order_cdek_delivery_address,
    }


def _refresh_status(db: Session, order: Order) -> None:
    """Подтянуть трек (cdek_number) и последний статус из CDEK."""
    if not order.order_cdek_uuid:
        return
    try:
        info = cdek.order_info(order.order_cdek_uuid)
    except cdek.CdekError:
        return
    track = info.get("cdek_number")
    if track:
        order.order_cdek_track_number = str(track)
    statuses = info.get("statuses") or []
    if statuses:
        latest = statuses[0]  # CDEK отдаёт статусы новейшим первым
        order.order_cdek_status = latest.get("name") or order.order_cdek_status
        order.order_cdek_status_updated_at = datetime.utcnow()
    db.commit()


def create_waybill(db: Session, order_id: int, payload, current_user: dict) -> dict:
    if not config.CDEK_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Интеграция СДЭК не настроена")
    order = _get_order_or_404(db, order_id)
    if order.order_cdek_uuid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="У заказа уже есть накладная СДЭК")
    _validate(payload)

    try:
        result = cdek.create_order(_build_payload(order, payload))
    except cdek.CdekError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    uuid = result.get("uuid")
    if not uuid:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"CDEK не вернул uuid: {result.get('requests')}")

    order.order_cdek_recipient_name = payload.recipient_name
    order.order_cdek_recipient_phone = payload.recipient_phone
    order.order_cdek_city_code = payload.city_code
    order.order_cdek_city_name = payload.city_name
    order.order_cdek_delivery_mode = payload.delivery_mode
    order.order_cdek_pvz_code = payload.pvz_code
    order.order_cdek_pvz_address = payload.pvz_address
    order.order_cdek_delivery_address = payload.delivery_address
    order.order_cdek_uuid = uuid
    order.order_cdek_status = "Создание накладной"
    order.order_cdek_status_updated_at = datetime.utcnow()
    db.commit()

    _refresh_status(db, order)  # трек/статус могут прийти не сразу — не страшно
    return _serialize(order)


def get_status(db: Session, order_id: int, *, refresh: bool = True) -> dict:
    order = _get_order_or_404(db, order_id)
    if refresh and order.order_cdek_uuid:
        _refresh_status(db, order)
    return _serialize(order)
