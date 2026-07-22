from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.contacts import ContactRepository
from app.schemas.common import build_pagination
from app.services.serializers import serialize_contact


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


def save_buyer_contact_from_order(db: Session, *, order_customer: str, order_info: str | None, order_establishment_id: int, order_method_id: int, order_sub_method: str | None, order_contact_method: str | None = None, order_sales_channel: str | None = None, current_user: dict) -> dict | None:
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