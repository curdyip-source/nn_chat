"""Создание накладной СДЭК для заказа и синхронизация статуса.

Собирает тело CDEK /orders из данных заказа + ввода пользователя, создаёт заказ в
СДЭК, сохраняет uuid/трек/статус в колонки order_cdek_*. Печать (2 накладные в чат)
и вебхуки — отдельными шагами.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from sqlalchemy.orm.attributes import flag_modified

from app.core import config
from app.core.audit_types import ENTITY_TYPE_CDEK, EVENT_TYPE_CDEK_WAYBILL_CREATE
from app.models.orders import Order
from app.repositories.audit_events import AuditEventRepository
from app.services import cdek
from app.services.audit import log_audit_event


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
                "payment": {"value": payload.cod_amount},  # наложенный платёж (за товар)
                "cost": payload.declared_value,             # объявленная стоимость
                "weight": payload.package.weight,
                "amount": 1,
            }],
        }],
    }
    # Имя/телефон отправителя — только если переопределяем договор (иначе CDEK берёт из
    # личного кабинета). На тест-среде config задан, на проде — пусто.
    if config.CDEK_SENDER_NAME:
        sender: dict = {"name": config.CDEK_SENDER_NAME}
        if config.CDEK_SENDER_PHONE:
            sender["phones"] = [{"number": config.CDEK_SENDER_PHONE}]
        body["sender"] = sender

    # Origin отправителя. Если оператор выбрал ПВЗ сдачи — шлём shipment_point (он задаёт
    # точку отправки, from_location тогда не нужен). Иначе — from_location по городу
    # (курьер/договор); CDEK принимает from_location по одному коду города.
    if payload.shipment_point:
        body["shipment_point"] = payload.shipment_point
    else:
        origin_code = payload.from_city_code or config.CDEK_SENDER_CITY_CODE
        from_location: dict = {"code": origin_code}
        # Точный адрес забора — из конфига и только для дефолтного origin (тест-среда/оверрайд).
        if config.CDEK_SENDER_ADDRESS and not payload.from_city_code:
            from_location["address"] = config.CDEK_SENDER_ADDRESS
        body["from_location"] = from_location

    if payload.comment:
        body["comment"] = payload.comment
    if payload.delivery_mode == "pvz":
        body["delivery_point"] = payload.pvz_code
    else:
        body["to_location"] = {"code": payload.city_code, "address": payload.delivery_address}

    # Доставку оплачивает получатель.
    if payload.delivery_paid_by_recipient and payload.delivery_cost > 0:
        body["delivery_recipient_cost"] = {"value": payload.delivery_cost}

    # Доп. услуги: страхование (param = объявленная стоимость), СМС-уведомление (param = телефон).
    services = []
    if payload.insurance and payload.declared_value > 0:
        services.append({"code": "INSURANCE", "parameter": str(int(payload.declared_value))})
    if payload.sms:
        services.append({"code": "SMS", "parameter": payload.recipient_phone})
    if services:
        body["services"] = services
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
        "from_city_code": order.order_cdek_from_city_code,
        "from_city_name": order.order_cdek_from_city_name,
        "shipment_point": order.order_cdek_shipment_point,
        "shipment_point_address": order.order_cdek_shipment_point_address,
    }


def record_waybill_track_in_audit(db: Session, order_id: int, track) -> None:
    """Дописать номер накладной в уже созданное событие аудита cdek.waybill.create.

    Трек СДЭК присваивает асинхронно — уже после create_waybill, — поэтому номер
    бэкфиллим в существующее событие (сохраняя автора-создателя), а не пишем новое
    событие без актора. Идемпотентно: патчим самое свежее событие без номера.
    """
    if not track:
        return
    rows, _ = AuditEventRepository(db).list(
        actor_user_id=None,
        entity_type=ENTITY_TYPE_CDEK,
        entity_id=order_id,
        event_type=EVENT_TYPE_CDEK_WAYBILL_CREATE,
        date_from=None,
        date_to=None,
        page=1,
        page_size=50,
    )
    for event in rows:  # новые сверху
        payload = dict(event.event_payload or {})
        if payload.get("cdek_track_number"):
            continue
        payload["cdek_track_number"] = str(track)
        event.event_payload = payload
        flag_modified(event, "event_payload")  # JSON-мутацию SQLAlchemy иначе не заметит
        db.commit()
        return


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
    # Если трек только что подтянулся — дописываем его в событие аудита о создании.
    record_waybill_track_in_audit(db, order.order_id, order.order_cdek_track_number)


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
    order.order_cdek_from_city_code = payload.from_city_code
    order.order_cdek_from_city_name = payload.from_city_name
    order.order_cdek_shipment_point = payload.shipment_point
    order.order_cdek_shipment_point_address = payload.shipment_point_address
    order.order_cdek_uuid = uuid
    order.order_cdek_status = "Создание накладной"
    order.order_cdek_status_updated_at = datetime.utcnow()
    db.commit()

    _refresh_status(db, order)  # трек/статус могут прийти не сразу — не страшно

    # Аудит: отдельная сущность «cdek» (в общем аудите — раздел СДЭК), но привязана к
    # заказу через entity_id, чтобы событие попало и в «Историю заказа». Номер накладной
    # (трек) кладём, если уже подтянулся; иначе останется uuid.
    log_audit_event(
        db,
        actor_user_id=current_user["user_id"],
        entity_type=ENTITY_TYPE_CDEK,
        entity_id=order_id,
        event_type=EVENT_TYPE_CDEK_WAYBILL_CREATE,
        event_payload={
            "order_id": order_id,
            "cdek_track_number": order.order_cdek_track_number,
            "cdek_uuid": uuid,
            "city_name": order.order_cdek_city_name,
            "recipient_name": order.order_cdek_recipient_name,
        },
    )

    # Печать (2 накладные) и постинг в чат заказа — в фоне (генерация PDF у CDEK асинхронна).
    from app.services import cdek_chat
    # Системного бота СДЭК заводим синхронно — при первом же создании накладной, чтобы он
    # существовал в базе независимо от фонового постинга (get-or-create, как fallback).
    cdek_chat.ensure_cdek_helper(db)
    cdek_chat.post_waybills_async(order_id)

    return _serialize(order)


def get_prefill(db: Session, customer: str) -> dict:
    """Автозаполнение СДЭК-данных для клиента: последние сохранённые из его прошлых заказов."""
    customer = (customer or "").strip()
    if not customer:
        return {}
    row = db.execute(
        select(Order)
        .where(Order.order_customer == customer)
        .where(Order.order_cdek_recipient_name.isnot(None) | Order.order_cdek_city_code.isnot(None))
        .order_by(desc(Order.order_created_at))
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return {}
    return {
        "recipient_name": row.order_cdek_recipient_name,
        "recipient_phone": row.order_cdek_recipient_phone,
        "city_code": row.order_cdek_city_code,
        "city_name": row.order_cdek_city_name,
        "delivery_mode": row.order_cdek_delivery_mode,
        "pvz_code": row.order_cdek_pvz_code,
        "pvz_address": row.order_cdek_pvz_address,
        "delivery_address": row.order_cdek_delivery_address,
    }


def delete_waybill(db: Session, order_id: int) -> dict:
    """Сбросить накладную СДЭК заказа, чтобы можно было создать заново.

    Пытается удалить заказ в CDEK (best-effort — невалидный/уже удалённый CDEK отвергнет,
    это не страшно), затем чистит uuid/трек/статус. Введённые данные (получатель, город,
    ПВЗ, origin) СОХРАНЯЕМ — форма пересоздания подставит их заново.
    """
    order = _get_order_or_404(db, order_id)
    if order.order_cdek_uuid:
        try:
            cdek.delete_order(order.order_cdek_uuid)
        except cdek.CdekError:
            pass  # у CDEK мог не удалиться (невалиден/уже нет) — всё равно чистим у себя
    order.order_cdek_uuid = None
    order.order_cdek_track_number = None
    order.order_cdek_status = None
    order.order_cdek_status_updated_at = None
    db.commit()
    from app.services.card_sync import notify_order_changed
    notify_order_changed(db, order.order_id)
    return _serialize(order)


def get_origin_default(db: Session) -> dict:
    """Дефолт отправителя (origin): последний использованный ПВЗ сдачи и его город —
    глобально по всем заказам, чтобы подставлять по умолчанию при создании накладной."""
    row = db.execute(
        select(Order)
        .where(Order.order_cdek_shipment_point.isnot(None))
        .order_by(desc(Order.order_created_at))
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return {}
    return {
        "from_city_code": row.order_cdek_from_city_code,
        "from_city_name": row.order_cdek_from_city_name,
        "shipment_point": row.order_cdek_shipment_point,
        "shipment_point_address": row.order_cdek_shipment_point_address,
    }


def get_status(db: Session, order_id: int, *, refresh: bool = True) -> dict:
    order = _get_order_or_404(db, order_id)
    if refresh and order.order_cdek_uuid:
        _refresh_status(db, order)
    return _serialize(order)


def handle_status_webhook(db: Session, body: dict) -> bool:
    """Приёмник вебхука CDEK ORDER_STATUS.

    CDEK шлёт событие с `uuid` заказа; сам статус в вебхуке приходит только кодом,
    поэтому проще перечитать заказ через order_info (свежий трек + русский статус) и
    пушнуть карточку в realtime. Возвращает True, если заказ найден и обновлён.
    """
    if not isinstance(body, dict):
        return False
    if body.get("type") not in (None, "ORDER_STATUS"):
        return False
    uuid = body.get("uuid") or (body.get("attributes") or {}).get("order_uuid")
    if not uuid:
        return False
    order = db.query(Order).filter(Order.order_cdek_uuid == str(uuid)).first()
    if order is None:
        return False
    _refresh_status(db, order)
    from app.services.card_sync import notify_order_changed
    notify_order_changed(db, order.order_id)
    return True
