from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_CONTACT, EVENT_TYPE_CONTACT_DELETE, EVENT_TYPE_CONTACT_UPDATE
from app.repositories.contacts import ContactRepository
from app.repositories.orders import OrderRepository
from app.schemas.common import build_pagination
from app.schemas.contacts import ContactUpdatePayload
from app.services.access_control import allowed_order_status_ids, can_delete_document, can_edit_document, list_visibility
from app.services.audit import log_audit_event
from app.services.card_sync import notify_order_changed
from app.services.domain_common import SOLD_ITEM_STATUS_NAME, get_establishment_or_404, get_order_method_or_404
from app.services.serializers import serialize_contact, serialize_order


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.replace("\xa0", " ").split())
    return normalized or None


def list_contacts(db: Session, *, contact_type: str, search: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    repository = ContactRepository(db)
    items, total = repository.list(contact_type=contact_type, search=search, page=page, page_size=page_size)
    return {"items": [serialize_contact(item) for item in items], "pagination": build_pagination(page, page_size, total)}


def create_or_get_contact(db: Session, *, contact_type: str, contact_name: str, contact_info: str | None = None, contact_establishment_id: int | None = None, contact_order_method_id: int | None = None, contact_order_sub_method: str | None = None, contact_contact_method: str | None = None, contact_sales_channel: str | None = None, current_user: dict | None = None) -> dict | None:
    normalized_name = _normalize_text(contact_name)
    if normalized_name is None:
        return None

    data = {
        "contact_type": contact_type,
        "contact_name": normalized_name,
        "contact_info": _normalize_text(contact_info),
        "contact_establishment_id": contact_establishment_id,
        "contact_order_method_id": contact_order_method_id,
        "contact_order_sub_method": _normalize_text(contact_order_sub_method),
        "contact_contact_method": _normalize_text(contact_contact_method),
        "contact_sales_channel": _normalize_text(contact_sales_channel),
        "contact_owner_user_id": current_user["user_id"] if current_user is not None else None,
    }

    repository = ContactRepository(db)
    existing = repository.find_exact(data=data)
    if existing is not None:
        # Способ связи и канал продаж — изменяемые атрибуты клиента, а не часть его
        # «личности»: при совпадении обновляем их, а не плодим дубликаты. Пустое
        # значение не затирает уже сохранённое.
        updates: dict = {}
        new_contact_method = data["contact_contact_method"]
        if new_contact_method is not None and new_contact_method != existing.contact_contact_method:
            updates["contact_contact_method"] = new_contact_method
        new_sales_channel = data["contact_sales_channel"]
        if new_sales_channel is not None and new_sales_channel != existing.contact_sales_channel:
            updates["contact_sales_channel"] = new_sales_channel
        if updates:
            existing = repository.update(existing, updates)
        return serialize_contact(existing)
    return serialize_contact(repository.create(data))


def save_buyer_contact_from_order(db: Session, *, order_customer: str, order_info: str | None, order_establishment_id: int, order_method_id: int | None, order_sub_method: str | None, order_contact_method: str | None = None, order_sales_channel: str | None = None, current_user: dict) -> dict | None:
    return create_or_get_contact(
        db,
        contact_type="buyer",
        contact_name=order_customer,
        contact_info=order_info,
        contact_establishment_id=order_establishment_id,
        contact_order_method_id=order_method_id,
        contact_order_sub_method=order_sub_method,
        contact_contact_method=order_contact_method,
        contact_sales_channel=order_sales_channel,
        current_user=current_user,
    )


def save_supplier_contact(db: Session, *, supplier_name: str | None, current_user: dict) -> dict | None:
    if supplier_name is None:
        return None
    return create_or_get_contact(db, contact_type="supplier", contact_name=supplier_name, current_user=current_user)


# --- Карточка контрагента: просмотр, правка, удаление, заказы покупателя ------


def _get_contact_or_404(db: Session, contact_id: int):
    row = ContactRepository(db).get_by_id(contact_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Контрагент не найден")
    return row


def _ensure_contact_permission(db: Session, row, current_user: dict, *, delete: bool) -> None:
    # Админ — всё. Контакт со складом — по профилю склада (edit_scope / delete_scope,
    # как у заказов: «свои» = созданные этим пользователем). Без склада — только автор.
    if current_user["user_admin"]:
        return
    owner_id = row.contact_owner_user_id
    if row.contact_establishment_id is not None and owner_id is not None:
        check = can_delete_document if delete else can_edit_document
        if check(db, current_user, row.contact_establishment_id, owner_id):
            return
    elif owner_id is not None and owner_id == current_user["user_id"]:
        return
    action = "удаления" if delete else "изменения"
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Недостаточно прав для {action} этого контрагента")


def get_contact(db: Session, contact_id: int) -> dict:
    return serialize_contact(_get_contact_or_404(db, contact_id))


def update_contact(db: Session, contact_id: int, payload: ContactUpdatePayload, current_user: dict) -> dict:
    row = _get_contact_or_404(db, contact_id)
    _ensure_contact_permission(db, row, current_user, delete=False)
    new_name = _normalize_text(payload.contact_name)
    if new_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Имя контрагента не может быть пустым")
    if payload.contact_establishment_id is not None:
        get_establishment_or_404(db, payload.contact_establishment_id)
    sub_method = _normalize_text(payload.contact_order_sub_method)
    if payload.contact_order_method_id is not None:
        method = get_order_method_or_404(db, payload.contact_order_method_id)
        if sub_method is not None and sub_method not in (method.order_method_sub_methods or []):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неизвестный подспособ заказа")
    else:
        sub_method = None

    data = {
        "contact_name": new_name,
        "contact_info": _normalize_text(payload.contact_info),
        "contact_establishment_id": payload.contact_establishment_id,
        "contact_order_method_id": payload.contact_order_method_id,
        "contact_order_sub_method": sub_method,
        "contact_contact_method": _normalize_text(payload.contact_contact_method),
        "contact_sales_channel": _normalize_text(payload.contact_sales_channel),
    }
    changed = [key for key, value in data.items() if getattr(row, key) != value]
    old_name = row.contact_name
    row = ContactRepository(db).update(row, data)

    # Заказы связаны с покупателем по имени — переименовываем и их, чтобы история
    # и сумма отгрузок остались за покупателем. Карточки заказов в чате обновляем.
    renamed_order_ids: list[int] = []
    if row.contact_type == "buyer" and old_name != new_name:
        renamed_order_ids = OrderRepository(db).rename_customer(old_name, new_name)
        for order_id in renamed_order_ids:
            notify_order_changed(db, order_id)

    if changed:
        log_audit_event(
            db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_CONTACT,
            entity_id=row.contact_id,
            event_type=EVENT_TYPE_CONTACT_UPDATE,
            event_payload={
                "changed_fields": changed,
                "old_name": old_name if old_name != new_name else None,
                "renamed_orders": len(renamed_order_ids),
            },
        )
    return serialize_contact(row)


def delete_contact(db: Session, contact_id: int, current_user: dict) -> None:
    # Удаляется только карточка контрагента; заказы остаются (в них имя — текстом).
    row = _get_contact_or_404(db, contact_id)
    _ensure_contact_permission(db, row, current_user, delete=True)
    snapshot = {"contact_type": row.contact_type, "contact_name": row.contact_name}
    ContactRepository(db).delete(row)
    log_audit_event(
        db,
        actor_user_id=current_user["user_id"],
        entity_type=ENTITY_TYPE_CONTACT,
        entity_id=contact_id,
        event_type=EVENT_TYPE_CONTACT_DELETE,
        event_payload=snapshot,
    )


def list_contact_orders(db: Session, contact_id: int, current_user: dict) -> dict:
    """Заказы покупателя (видимые пользователю) с позициями + сумма отгруженного по валютам."""
    row = _get_contact_or_404(db, contact_id)
    if row.contact_type != "buyer":
        return {"items": [], "shipped_totals": []}
    # Те же ограничения, что в разделе «Заказы»: склады (ось B) и статусы (ось C).
    allowed_statuses = allowed_order_status_ids(current_user)
    if allowed_statuses is not None and not allowed_statuses:
        return {"items": [], "shipped_totals": []}
    scoped_full_ids, scoped_own_ids, scoped_user_id = list_visibility(db, current_user)
    scope = {
        "status_ids": list(allowed_statuses) if allowed_statuses is not None else None,
        "scoped_full_ids": scoped_full_ids,
        "scoped_own_ids": scoped_own_ids,
        "scoped_user_id": scoped_user_id,
    }
    repository = OrderRepository(db)
    orders = repository.list_by_customer(row.contact_name, **scope)
    totals = repository.shipped_totals_by_customer(row.contact_name, shipped_status_name=SOLD_ITEM_STATUS_NAME, **scope)
    return {
        "items": [serialize_order(order) for order in orders],
        "shipped_totals": [
            {"currency_id": currency_id, "currency_sign": currency_sign, "amount": amount}
            for currency_id, currency_sign, amount in totals
            if amount
        ],
    }
