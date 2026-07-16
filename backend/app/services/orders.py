import logging
from collections import Counter
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_CDEK, ENTITY_TYPE_ORDER, EVENT_TYPE_CDEK_WAYBILL_CREATE, EVENT_TYPE_ORDER_COMMENT_CREATE, EVENT_TYPE_ORDER_COMMENT_DELETE, EVENT_TYPE_ORDER_COMMENT_UPDATE, EVENT_TYPE_ORDER_CREATE, EVENT_TYPE_ORDER_DELETE, EVENT_TYPE_ORDER_UPDATE
from app.models.messages import Message
from app.models.orders import Order, OrderItem
from app.repositories.audit_events import AuditEventRepository
from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.repositories.messages import MessageRepository
from app.repositories.orders import OrderRepository
from app.repositories.reference_data import ReferenceDataRepository
from app.schemas.common import build_pagination
from app.schemas.orders import OrderCommentCreatePayload, OrderCommentUpdatePayload, OrderCreatePayload, OrderStatusUpdatePayload, OrderUpdatePayload
from app.services.contacts import save_buyer_contact_from_order, save_supplier_contact
from app.services.audit import log_audit_event
from app.services.access_control import allowed_order_status_ids, can_create_on_establishment, can_delete_document, can_edit_document, can_view_document, can_view_order_status, list_visibility
from app.services.card_sync import notify_cards_deleted, notify_order_changed
from app.services.domain_common import get_default_currency_or_400, get_default_status_or_400, get_establishment_or_404, get_order_method_or_404, get_status_or_404, resolve_product_snapshot
from app.services.messages import resolve_mention_recipient_ids
from app.services.push_notifications import send_mention_push_event, send_order_change_push_event, send_order_comment_push_event, send_push_notification_event
from app.services.serializers import serialize_datetime, serialize_order, serialize_order_comment


logger = logging.getLogger("app.orders")


ALLOWED_ORDER_CONTACT_METHODS = ("WA", "TG", "AV", "IG", "SMS", "MX")


def _normalize_order_contact_method(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    if normalized not in ALLOWED_ORDER_CONTACT_METHODS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неизвестный способ связи")
    return normalized


def _order_item_identity(item: dict) -> str:
    # Идентичность позиции — по артикулу (он стабилен), иначе по названию. НЕ по
    # product_id: при федерации каталога товар переподвязывается и product_id меняется
    # (NULL→id), из-за чего смена статуса ложно выглядела как «убрал+добавил все позиции».
    article = (item.get("order_item_article") or "").strip().lower()
    if article:
        return f"a:{article}"
    name = (item.get("order_item_name") or "").strip().lower()
    return f"n:{name}"


def _count_order_item_changes(before_items: list[dict], after_items: list[dict]) -> tuple[int, int]:
    before_counts = Counter(_order_item_identity(item) for item in before_items)
    after_counts = Counter(_order_item_identity(item) for item in after_items)
    added_count = sum((after_counts - before_counts).values())
    removed_count = sum((before_counts - after_counts).values())
    return added_count, removed_count


ORDER_AUDIT_FIELDS = (
    "order_establishment_id",
    "order_establishment_name",
    "order_method_id",
    "order_method_name",
    "order_sub_method",
    "order_contact_method",
    "order_customer",
    "order_info",
    "order_status_id",
    "order_status",
)

ORDER_ITEM_AUDIT_FIELDS = (
    "order_item_product_id",
    "order_item_name",
    "order_item_article",
    "order_item_quantity",
    "order_item_price",
    "order_item_status_id",
    "order_item_status",
    "order_item_note",
    "order_item_source_establishment_id",
    "order_item_source_establishment_name",
    "order_item_destination_establishment_id",
    "order_item_destination_establishment_name",
    "order_item_currency_id",
    "order_item_checkpoint_started",
    "order_item_checkpoint_completed",
)


def _build_order_item_identity(item: dict, sequence: int) -> str:
    # По артикулу (стабилен при федерации), иначе по названию — не по product_id,
    # который меняется при переподвязке товара к свежему каталогу.
    article = (item.get("order_item_article") or "").strip().lower()
    name = (item.get("order_item_name") or "").strip().lower()
    base = f"a:{article}" if article else f"n:{name}"
    return f"{base}#{sequence}"


def _summarize_order_item_for_audit(item: dict) -> dict:
    return {field: item.get(field) for field in ORDER_ITEM_AUDIT_FIELDS}


def _build_order_item_map(items: list[dict]) -> dict[str, dict]:
    counts: dict[str, int] = {}
    mapped: dict[str, dict] = {}
    for item in items:
        if item.get("order_item_product_id") is not None:
            base = f"product:{item['order_item_product_id']}"
        else:
            base = f"manual:{item.get('order_item_article') or ''}:{item.get('order_item_name') or ''}"
        counts[base] = counts.get(base, 0) + 1
        mapped[_build_order_item_identity(item, counts[base])] = item
    return mapped


def _build_order_audit_changes(before: dict, after: dict) -> dict:
    changes: dict[str, dict] = {}
    for field in ORDER_AUDIT_FIELDS:
        before_value = before.get(field)
        after_value = after.get(field)
        if before_value != after_value:
            changes[field] = {"from": before_value, "to": after_value}
    return changes


def _normalize_order_item_note(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.splitlines()).strip()
    return normalized or None


def _build_order_item_audit_changes(before_items: list[dict], after_items: list[dict]) -> dict:
    before_map = _build_order_item_map(before_items)
    after_map = _build_order_item_map(after_items)

    added = [
        {"item_key": item_key, "after": _summarize_order_item_for_audit(after_map[item_key])}
        for item_key in after_map.keys() - before_map.keys()
    ]
    removed = [
        {"item_key": item_key, "before": _summarize_order_item_for_audit(before_map[item_key])}
        for item_key in before_map.keys() - after_map.keys()
    ]

    updated = []
    for item_key in before_map.keys() & after_map.keys():
        before_item = before_map[item_key]
        after_item = after_map[item_key]
        item_changes = {}
        for field in ORDER_ITEM_AUDIT_FIELDS:
            before_value = before_item.get(field)
            after_value = after_item.get(field)
            if before_value != after_value:
                item_changes[field] = {"from": before_value, "to": after_value}

        if item_changes:
            updated.append(
                {
                    "item_key": item_key,
                    "changes": item_changes,
                    "before": _summarize_order_item_for_audit(before_item),
                    "after": _summarize_order_item_for_audit(after_item),
                }
            )

    return {
        "before_count": len(before_items),
        "after_count": len(after_items),
        "added": sorted(added, key=lambda item: item["item_key"]),
        "removed": sorted(removed, key=lambda item: item["item_key"]),
        "updated": sorted(updated, key=lambda item: item["item_key"]),
    }


def _build_order_create_audit_payload(order_data: dict, message_id: int) -> dict:
    return {
        "message_id": message_id,
        "order": {field: order_data.get(field) for field in ORDER_AUDIT_FIELDS},
        "items_count": len(order_data.get("items", [])),
        "items": [_summarize_order_item_for_audit(item) for item in order_data.get("items", [])],
    }


def _save_supplier_contacts_from_items(db: Session, *, items: list[dict], current_user: dict) -> None:
    supplier_names = {
        supplier_name
        for supplier_name in (item.get("order_item_supplier") for item in items)
        if supplier_name is not None and supplier_name.strip()
    }
    for supplier_name in supplier_names:
        save_supplier_contact(db, supplier_name=supplier_name, current_user=current_user)


def _build_order_update_audit_payload(before: dict, after: dict) -> dict:
    return {
        "changed_fields": _build_order_audit_changes(before, after),
        "items": _build_order_item_audit_changes(before.get("items", []), after.get("items", [])),
    }


def _order_history_actor(event) -> tuple[str | None, str]:
    # ФИО актора (как в чате: «Фамилия Имя»), fallback — логин, затем «Система».
    actor = getattr(event, "actor", None)
    if actor is None:
        return None, "Система"
    full = " ".join(part for part in (actor.user_second_name, actor.user_first_name) if part).strip()
    return actor.user_login, (full or actor.user_login or "Пользователь")


def _order_update_history_texts(payload: dict) -> list[tuple[str, str]]:
    # Разворачиваем один order.update в набор человекочитаемых действий.
    if payload.get("action") == "split":
        return [("split", "разделил заказ")]

    texts: list[tuple[str, str]] = []
    changed = payload.get("changed_fields") or {}
    items = payload.get("items") or {}

    # 1) Статус самого заказа.
    if "order_status" in changed:
        new_status = changed["order_status"].get("to")
        texts.append(("order_status", f"сменил статус заказа на «{new_status}»" if new_status else "сменил статус заказа"))

    # 2) Статусы товаров — группируем по новому статусу, перечисляя наименования,
    #    чтобы было видно, какой именно товар сменил статус.
    status_to_names: dict[str, list[str]] = {}
    for upd in items.get("updated", []):
        changes = upd.get("changes") or {}
        if "order_item_status" not in changes:
            continue
        new_status = changes["order_item_status"].get("to")
        name = (upd.get("after") or {}).get("order_item_name") or (upd.get("before") or {}).get("order_item_name") or "товар"
        status_to_names.setdefault(new_status or "", []).append(name)

    for new_status, names in status_to_names.items():
        suffix = f" на «{new_status}»" if new_status else ""
        if len(names) == 1:
            texts.append(("item_status", f"сменил статус товара «{names[0]}»{suffix}"))
        else:
            listed = ", ".join(f"«{name}»" for name in names)
            texts.append(("item_status", f"сменил статус товаров{suffix}: {listed}"))

    # 3) Прочие правки (добавление/удаление позиций или изменение полей, не связанных со статусом).
    other_header = any(field != "order_status" and not field.endswith("_id") for field in changed)
    other_items = bool(items.get("added")) or bool(items.get("removed")) or any(
        field != "order_item_status" and not field.endswith("_id")
        for upd in items.get("updated", [])
        for field in (upd.get("changes") or {})
    )
    if other_header or other_items:
        texts.append(("edit", "отредактировал заказ"))

    # Update без распознанных изменений всё равно показываем как правку.
    if not texts:
        texts.append(("edit", "отредактировал заказ"))
    return texts


def _order_history_entries_for_event(event) -> list[dict]:
    actor_login, actor_name = _order_history_actor(event)
    created_at = serialize_datetime(event.created_at)
    payload = event.event_payload or {}

    if event.event_type == EVENT_TYPE_ORDER_CREATE:
        actions = [("create", "создал заказ")]
    elif event.event_type == EVENT_TYPE_ORDER_UPDATE:
        actions = _order_update_history_texts(payload)
    elif event.event_type == EVENT_TYPE_ORDER_DELETE:
        actions = [("delete", "удалил заказ")]
    elif event.event_type == EVENT_TYPE_ORDER_COMMENT_CREATE:
        actions = [("comment", "написал в чат заказа")]
    elif event.event_type == EVENT_TYPE_ORDER_COMMENT_UPDATE:
        actions = [("comment", "изменил сообщение в чате заказа")]
    elif event.event_type == EVENT_TYPE_ORDER_COMMENT_DELETE:
        actions = [("comment", "удалил сообщение из чата заказа")]
    elif event.event_type == EVENT_TYPE_CDEK_WAYBILL_CREATE:
        track = payload.get("cdek_track_number")
        actions = [("cdek", f"создал накладную СДЭК №{track}" if track else "создал накладную СДЭК")]
    else:
        actions = []

    return [
        {
            "audit_event_id": event.audit_event_id,
            "kind": kind,
            "text": text,
            "actor_user_login": actor_login,
            "actor_name": actor_name,
            "created_at": created_at,
        }
        for kind, text in actions
    ]


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)
        self.message_repository = MessageRepository(db)
        self.attachment_asset_repository = MessageAttachmentAssetRepository(db)

    def get_order_or_404(self, order_id: int):
        row = self.repository.get_by_id(order_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
        return row

    def get_accessible_order_or_404(self, order_id: int, current_user: dict):
        # Область видимости (профиль view_scope): заказ вне области → 404 (не раскрываем).
        row = self.get_order_or_404(order_id)
        if not can_view_document(self.db, current_user, row.order_establishment_id, row.order_owner_user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
        # Гейтинг по статусу заказа (ось C): статус вне разрешённого набора → 404 (не раскрываем).
        if not can_view_order_status(current_user, row.order_status_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
        return row

    def _ensure_order_editable(self, row, current_user: dict) -> None:
        # Право на редактирование (профиль edit_scope).
        if not can_edit_document(self.db, current_user, row.order_establishment_id, row.order_owner_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для изменения этого заказа")

    def list_orders(self, current_user: dict, *, page: int = 1, page_size: int = 20, status_ids: list[int] | None = None, method_ids: list[int] | None = None, establishment_ids: list[int] | None = None, search: str | None = None, date_from: date | None = None, date_to: date | None = None) -> dict:
        # Гейтинг по статусу заказа (ось C): пересекаем запрошенный фильтр статусов с разрешёнными.
        # Пустое пересечение (запросили только недоступные статусы) → отдаём пустой список.
        allowed_statuses = allowed_order_status_ids(current_user)
        if allowed_statuses is not None:
            status_ids = [s for s in status_ids if s in allowed_statuses] if status_ids else list(allowed_statuses)
            if not status_ids:
                return {"items": [], "pagination": build_pagination(page, page_size, 0), "totals": []}
        # Область видимости per-warehouse: (склады «видны все» | склады «только свои» | user).
        scoped_full_ids, scoped_own_ids, scoped_user_id = list_visibility(self.db, current_user)
        rows, total = self.repository.list(page=page, page_size=page_size, status_ids=status_ids, method_ids=method_ids, establishment_ids=establishment_ids, scoped_full_ids=scoped_full_ids, scoped_own_ids=scoped_own_ids, scoped_user_id=scoped_user_id, search=search, date_from=date_from, date_to=date_to)
        currency_totals = self.repository.totals_by_currency(status_ids=status_ids, method_ids=method_ids, establishment_ids=establishment_ids, scoped_full_ids=scoped_full_ids, scoped_own_ids=scoped_own_ids, scoped_user_id=scoped_user_id, search=search, date_from=date_from, date_to=date_to)
        totals = [
            {"currency_id": currency_id, "currency_sign": currency_sign, "amount": amount}
            for currency_id, currency_sign, amount in currency_totals
            if amount
        ]
        return {"items": [serialize_order(item) for item in rows], "pagination": build_pagination(page, page_size, total), "totals": totals}

    def create_order(self, payload: OrderCreatePayload, current_user: dict) -> dict:
        get_establishment_or_404(self.db, payload.order_establishment_id)
        if not can_create_on_establishment(self.db, current_user, payload.order_establishment_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для создания заказа на этом складе")
        order_method_row = get_order_method_or_404(self.db, payload.order_method_id)
        available_sub_methods = order_method_row.order_method_sub_methods or []
        normalized_order_sub_method = payload.order_sub_method.strip() if payload.order_sub_method else None
        if not available_sub_methods and normalized_order_sub_method is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для выбранного способа заказа подспособ не поддерживается")
        if normalized_order_sub_method is not None and normalized_order_sub_method not in available_sub_methods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неизвестный подспособ заказа")
        normalized_order_contact_method = _normalize_order_contact_method(payload.order_contact_method)
        status_row = get_status_or_404(self.db, payload.order_status_id, expected_type="orders") if payload.order_status_id else get_default_status_or_400(self.db, status_type="orders")
        default_currency = get_default_currency_or_400(self.db)
        default_item_status = get_default_status_or_400(self.db, status_type="order_products")
        items = []
        for item in payload.items:
            product_row, article, name, price = resolve_product_snapshot(
                self.db,
                current_user=current_user,
                product_id=item.product_id,
                product_article=item.product_article,
                product_name=item.product_name,
                product_cost_usd=item.order_item_price,
            )
            item_status = get_status_or_404(self.db, item.order_item_status_id, expected_type="order_products") if item.order_item_status_id else default_item_status
            normalized_item_supplier = item.order_item_supplier.strip() if item.order_item_supplier else None
            normalized_item_note = _normalize_order_item_note(item.order_item_note)
            if item_status.status_status not in ("Заказ поставщику", "Заказано"):
                normalized_item_supplier = None
            source_establishment_id, destination_establishment_id = self._resolve_item_route(item_status.status_status if item_status else None, item.order_item_source_establishment_id, item.order_item_destination_establishment_id)
            items.append(
                {
                    "order_item_product_id": product_row.product_id,
                    "order_item_name": name,
                    "order_item_article": article,
                    "order_item_quantity": item.order_item_quantity,
                    "order_item_price": price,
                    "order_item_status_id": item_status.status_id,
                    "order_item_supplier": normalized_item_supplier,
                    "order_item_note": normalized_item_note,
                    "order_item_source_establishment_id": source_establishment_id,
                    "order_item_destination_establishment_id": destination_establishment_id,
                    "order_item_currency_id": item.order_item_currency_id or default_currency.currency_id,
                    "order_item_checkpoint_started": item.order_item_checkpoint_started,
                    "order_item_checkpoint_completed": item.order_item_checkpoint_completed,
                    "order_item_owner_user_id": current_user["user_id"],
                }
            )

        cdek = payload.cdek
        row = self.repository.create(
            {
                "order_establishment_id": payload.order_establishment_id,
                "order_method_id": payload.order_method_id,
                "order_sub_method": normalized_order_sub_method,
                "order_contact_method": normalized_order_contact_method,
                "order_customer": payload.order_customer,
                "order_info": payload.order_info,
                "order_status_id": status_row.status_id,
                "order_owner_user_id": current_user["user_id"],
                "order_cdek_recipient_name": cdek.recipient_name if cdek else None,
                "order_cdek_recipient_phone": cdek.recipient_phone if cdek else None,
                "order_cdek_city_code": cdek.city_code if cdek else None,
                "order_cdek_city_name": cdek.city_name if cdek else None,
                "order_cdek_delivery_mode": cdek.delivery_mode if cdek else None,
                "order_cdek_pvz_code": cdek.pvz_code if cdek else None,
                "order_cdek_pvz_address": cdek.pvz_address if cdek else None,
                "order_cdek_delivery_address": cdek.delivery_address if cdek else None,
            },
            items,
        )
        _save_supplier_contacts_from_items(self.db, items=items, current_user=current_user)
        if payload.save_contact:
            save_buyer_contact_from_order(
                self.db,
                order_customer=payload.order_customer,
                order_info=payload.order_info,
                order_establishment_id=payload.order_establishment_id,
                order_method_id=payload.order_method_id,
                order_sub_method=normalized_order_sub_method,
                order_contact_method=normalized_order_contact_method,
                current_user=current_user,
            )
        message = self.message_repository.create(
            {
                "message_type": "order",
                "message_text": payload.message_text.strip() if payload.message_text else None,
                "message_owner_user_id": current_user["user_id"],
                "message_order_id": row.order_id,
            }
        )
        result = serialize_order(row)
        result["message_id"] = message.message_id
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=row.order_id,
            event_type=EVENT_TYPE_ORDER_CREATE,
            event_payload=_build_order_create_audit_payload(result, message.message_id),
        )
        try:
            send_push_notification_event(
                self.db,
                excluded_user_id=current_user["user_id"],
                message_type="order",
                sender_name=f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"],
                message_text=payload.message_text,
                entity_id=row.order_id,
            )
        except Exception:
            logger.exception(
                "push.dispatch_failed",
                extra={
                    "event_type": "push.dispatch_failed",
                    "entity_type": "order",
                    "order_id": row.order_id,
                    "user_id": current_user["user_id"],
                },
            )
        return result

    def update_order(self, order_id: int, payload: OrderUpdatePayload, current_user: dict) -> dict:
        row = self.get_accessible_order_or_404(order_id, current_user)
        self._ensure_order_editable(row, current_user)
        before_snapshot = serialize_order(row)
        get_establishment_or_404(self.db, payload.order_establishment_id)
        order_method_row = get_order_method_or_404(self.db, payload.order_method_id)
        available_sub_methods = order_method_row.order_method_sub_methods or []
        normalized_order_sub_method = payload.order_sub_method.strip() if payload.order_sub_method else None
        if not available_sub_methods and normalized_order_sub_method is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для выбранного способа заказа подспособ не поддерживается")
        if normalized_order_sub_method is not None and normalized_order_sub_method not in available_sub_methods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неизвестный подспособ заказа")
        normalized_order_contact_method = _normalize_order_contact_method(payload.order_contact_method)

        status_row = get_status_or_404(self.db, payload.order_status_id, expected_type="orders")
        default_currency = get_default_currency_or_400(self.db)
        default_item_status = get_default_status_or_400(self.db, status_type="order_products")
        items = []
        for item in payload.items:
            product_row, article, name, price = resolve_product_snapshot(
                self.db,
                current_user=current_user,
                product_id=item.product_id,
                product_article=item.product_article,
                product_name=item.product_name,
                product_cost_usd=item.order_item_price,
            )
            item_status = get_status_or_404(self.db, item.order_item_status_id, expected_type="order_products") if item.order_item_status_id else default_item_status
            normalized_item_supplier = item.order_item_supplier.strip() if item.order_item_supplier else None
            normalized_item_note = _normalize_order_item_note(item.order_item_note)
            if item_status.status_status not in ("Заказ поставщику", "Заказано"):
                normalized_item_supplier = None
            source_establishment_id, destination_establishment_id = self._resolve_item_route(item_status.status_status if item_status else None, item.order_item_source_establishment_id, item.order_item_destination_establishment_id)
            items.append(
                {
                    "order_item_product_id": product_row.product_id,
                    "order_item_name": name,
                    "order_item_article": article,
                    "order_item_quantity": item.order_item_quantity,
                    "order_item_price": price,
                    "order_item_status_id": item_status.status_id,
                    "order_item_supplier": normalized_item_supplier,
                    "order_item_note": normalized_item_note,
                    "order_item_source_establishment_id": source_establishment_id,
                    "order_item_destination_establishment_id": destination_establishment_id,
                    "order_item_currency_id": item.order_item_currency_id or default_currency.currency_id,
                    "order_item_checkpoint_started": item.order_item_checkpoint_started,
                    "order_item_checkpoint_completed": item.order_item_checkpoint_completed,
                    "order_item_owner_user_id": current_user["user_id"],
                }
            )

        row = self.repository.update_with_items(
            row,
            {
                "order_establishment_id": payload.order_establishment_id,
                "order_method_id": payload.order_method_id,
                "order_sub_method": normalized_order_sub_method,
                "order_contact_method": normalized_order_contact_method,
                "order_customer": payload.order_customer,
                "order_info": payload.order_info,
                "order_status_id": status_row.status_id,
            },
            items,
        )
        _save_supplier_contacts_from_items(self.db, items=items, current_user=current_user)
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=row.order_id,
            event_type=EVENT_TYPE_ORDER_UPDATE,
            event_payload=_build_order_update_audit_payload(before_snapshot, serialize_order(row)),
        )

        added_count, removed_count = _count_order_item_changes(before_snapshot.get("items", []), items)
        if added_count or removed_count:
            try:
                send_order_change_push_event(
                    self.db,
                    excluded_user_id=current_user["user_id"],
                    sender_name=f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"],
                    order_id=row.order_id,
                    added_count=added_count,
                    removed_count=removed_count,
                )
            except Exception:
                logger.exception(
                    "push.order_change_dispatch_failed",
                    extra={
                        "event_type": "push.order_change_dispatch_failed",
                        "order_id": row.order_id,
                        "user_id": current_user["user_id"],
                    },
                )

        notify_order_changed(self.db, row.order_id)
        return serialize_order(row)

    def update_order_status(self, order_id: int, payload: OrderStatusUpdatePayload, current_user: dict) -> dict:
        row = self.get_accessible_order_or_404(order_id, current_user)
        self._ensure_order_editable(row, current_user)
        before_snapshot = serialize_order(row)
        status_row = get_status_or_404(self.db, payload.order_status_id, expected_type="orders")
        # Гейтинг по статусу заказа (ось C): переводить можно только в разрешённые статусы.
        if not can_view_order_status(current_user, status_row.status_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для перевода заказа в этот статус")
        row = self.repository.update(row, {"order_status_id": status_row.status_id})
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=row.order_id,
            event_type=EVENT_TYPE_ORDER_UPDATE,
            event_payload=_build_order_update_audit_payload(before_snapshot, serialize_order(row)),
        )
        notify_order_changed(self.db, row.order_id)
        return serialize_order(row)

    def get_order_history(self, order_id: int, current_user: dict) -> dict:
        # Проверка доступа к заказу (область видимости + гейтинг по статусу).
        self.get_accessible_order_or_404(order_id, current_user)
        repo = AuditEventRepository(self.db)
        # События самого заказа + события СДЭК (отдельная сущность аудита, но привязана к
        # заказу через entity_id — накладные показываем в той же ленте истории).
        order_rows, _ = repo.list(
            actor_user_id=None, entity_type=ENTITY_TYPE_ORDER, entity_id=order_id,
            event_type=None, date_from=None, date_to=None, page=1, page_size=500,
        )
        cdek_rows, _ = repo.list(
            actor_user_id=None, entity_type=ENTITY_TYPE_CDEK, entity_id=order_id,
            event_type=None, date_from=None, date_to=None, page=1, page_size=500,
        )
        # Сливаем обе ленты, новые сверху (created_at убыв.; при равенстве — по id убыв.).
        rows = sorted(
            [*order_rows, *cdek_rows],
            key=lambda event: (event.created_at, event.audit_event_id),
            reverse=True,
        )
        items = [entry for event in rows for entry in _order_history_entries_for_event(event)]
        return {"items": items}

    def delete_order(self, order_id: int, current_user: dict) -> None:
        row = self.get_accessible_order_or_404(order_id, current_user)
        # Право на удаление (профиль delete_scope).
        if not can_delete_document(self.db, current_user, row.order_establishment_id, row.order_owner_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для удаления этого заказа")
        snapshot = serialize_order(row)
        # 1) Карточки заказа в чате гасим мягко (tombstone для дельта-синка) и отвязываем
        #    от заказа, чтобы каскад при удалении заказа их физически не снёс.
        message_ids = self.message_repository.soft_delete_for_order(order_id)
        # 2) Жёсткое удаление заказа — позиции и комментарии уходят каскадом.
        self.repository.delete(row)
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=order_id,
            event_type=EVENT_TYPE_ORDER_DELETE,
            event_payload={
                "order_customer": snapshot.get("order_customer"),
                "order_status": snapshot.get("order_status"),
                "items_count": len(snapshot.get("items", [])),
            },
        )
        # 3) Realtime: убрать погашенные карточки из ленты у всех подключённых клиентов.
        notify_cards_deleted(message_ids)

    def list_order_comments(self, order_id: int, current_user: dict) -> dict:
        row = self.get_accessible_order_or_404(order_id, current_user)
        items = sorted(
            row.comments,
            key=lambda item: (item.order_comment_created_at.isoformat() if item.order_comment_created_at else "", item.order_comment_id),
        )
        return {"items": [serialize_order_comment(item) for item in items]}

    def add_order_comment(self, order_id: int, payload: OrderCommentCreatePayload, current_user: dict, *, enforce_access: bool = True) -> dict:
        # enforce_access=False — для системных постов (бот СДЭК кладёт накладные в чат
        # заказа): у бота нет ролей на складах, поэтому проверку видимости пропускаем,
        # но существование заказа всё равно требуем.
        if enforce_access:
            self.get_accessible_order_or_404(order_id, current_user)
        else:
            self.get_order_or_404(order_id)
        attachments = []
        for item in payload.attachments:
            asset = self.attachment_asset_repository.get_by_storage_key(item.attachment_storage_key)
            if asset is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вложение не найдено")
            if asset.attachment_asset_owner_user_id != current_user["user_id"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для вложения")
            if asset.attachment_asset_kind != item.attachment_kind:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Тип вложения не совпадает")

            attachments.append(
                {
                    "attachment_owner_user_id": current_user["user_id"],
                    "attachment_kind": asset.attachment_asset_kind,
                    "attachment_original_filename": asset.attachment_asset_original_filename,
                    "attachment_mime_type": asset.attachment_asset_mime_type,
                    "attachment_storage_key": asset.attachment_asset_storage_key,
                    "attachment_size_bytes": asset.attachment_asset_size_bytes,
                }
            )

        row = self.repository.add_comment(
            order_id,
            {
                "order_comment_text": payload.order_comment_text.strip() if payload.order_comment_text else "",
                "order_comment_owner_user_id": current_user["user_id"],
            },
            attachments=attachments,
        )
        # Комментарий меняет карточку заказа: бампаем message_updated_at (дельта-синк
        # подхватит) и публикуем SSE-событие updated с обновлённой карточкой, включающей
        # новый комментарий. Без этого счётчик комментариев на карточке в ленте не
        # обновляется в реалтайме (и не подтягивается даже после перезапуска — курсор
        # синка не двигается). Как в update_order / update_order_status.
        notify_order_changed(self.db, order_id)
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=order_id,
            event_type=EVENT_TYPE_ORDER_COMMENT_CREATE,
            event_payload={
                "order_comment_id": row.order_comment_id,
                "order_comment_text": row.order_comment_text,
                "attachment_count": len(attachments),
            },
        )
        sender_name = f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"]
        mention_recipient_ids: list[int] = []
        try:
            mention_recipient_ids = resolve_mention_recipient_ids(
                self.db,
                mentioned_user_ids=payload.mentioned_user_ids,
                sender_user_id=current_user["user_id"],
            )
            if mention_recipient_ids:
                send_mention_push_event(
                    self.db,
                    recipient_user_ids=mention_recipient_ids,
                    sender_name=sender_name,
                    context="order",
                    entity_id=order_id,
                )
        except Exception:
            logger.exception(
                "push.mention_dispatch_failed",
                extra={
                    "event_type": "push.mention_dispatch_failed",
                    "order_id": order_id,
                    "user_id": current_user["user_id"],
                },
            )
        # Общий пуш о новом комментарии — всем активным, кроме автора и уже упомянутых
        # (упомянутые получили более конкретный пуш выше — не дублируем).
        try:
            send_order_comment_push_event(
                self.db,
                excluded_user_ids={current_user["user_id"], *mention_recipient_ids},
                sender_name=sender_name,
                order_id=order_id,
                comment_text=row.order_comment_text,
                has_attachments=bool(attachments),
            )
        except Exception:
            logger.exception(
                "push.order_comment_dispatch_failed",
                extra={
                    "event_type": "push.order_comment_dispatch_failed",
                    "order_id": order_id,
                    "user_id": current_user["user_id"],
                },
            )
        return serialize_order_comment(row)

    def update_order_comment(self, order_id: int, comment_id: int, payload: OrderCommentUpdatePayload, current_user: dict) -> dict:
        # Заказ должен быть в области видимости, иначе не раскрываем его существование.
        self.get_accessible_order_or_404(order_id, current_user)
        comment = self.repository.get_comment_by_id(comment_id)
        if comment is None or comment.order_comment_order_id != order_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
        # Редактировать можно только своё текстовое сообщение без вложений — как в чате.
        if comment.order_comment_owner_user_id != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Можно изменить только своё сообщение")
        if comment.attachments:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно изменить только текстовое сообщение")
        previous_text = comment.order_comment_text
        updated = self.repository.update_comment(comment, {"order_comment_text": payload.order_comment_text.strip()})
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=order_id,
            event_type=EVENT_TYPE_ORDER_COMMENT_UPDATE,
            event_payload={
                "order_comment_id": updated.order_comment_id,
                "previous_order_comment_text": previous_text,
                "order_comment_text": updated.order_comment_text,
            },
        )
        # Обновлённый текст меняет карточку заказа — публикуем SSE-событие updated
        # (дельта-синк подхватит), как в add_order_comment/delete_order_comment.
        notify_order_changed(self.db, order_id)
        return serialize_order_comment(updated)

    def delete_order_comment(self, order_id: int, comment_id: int, current_user: dict) -> None:
        # Заказ должен быть в области видимости, иначе не раскрываем его существование.
        self.get_accessible_order_or_404(order_id, current_user)
        comment = self.repository.get_comment_by_id(comment_id)
        if comment is None or comment.order_comment_order_id != order_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
        # Право на удаление — как у чат-сообщений: своё удаляет автор, чужое — только админ.
        if comment.order_comment_owner_user_id != current_user["user_id"] and not current_user["user_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Удалять чужие сообщения может только администратор")
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=order_id,
            event_type=EVENT_TYPE_ORDER_COMMENT_DELETE,
            event_payload={
                "order_comment_id": comment.order_comment_id,
                "order_comment_text": comment.order_comment_text,
                "attachment_count": len(comment.attachments),
            },
        )
        self.repository.delete_comment(comment)
        # Комментарий убран из карточки заказа — бампаем message_updated_at и публикуем
        # SSE-событие updated с обновлённой карточкой (дельта-синк подхватит), как в
        # add_order_comment. Иначе счётчик комментариев в ленте не обновится в реалтайме.
        notify_order_changed(self.db, order_id)

    def split_order(self, order_id: int, current_user: dict) -> dict:
        """Разделить заказ для частичной отгрузки: товары, готовые к отгрузке сейчас
        («В наличии» и уже «Собрано»), остаются в этом заказе и он переводится в «На
        сборку»; всё остальное (ожидаемые + отменённые) уходит в новый заказ-дубль со
        статусом исходного. Статусы остающихся позиций сохраняются («Собрано» не
        сбрасывается). Атомарно — один commit."""
        order = self.get_accessible_order_or_404(order_id, current_user)
        self._ensure_order_editable(order, current_user)

        reference = ReferenceDataRepository(self.db)
        in_stock_status = reference.get_status_by_type_and_name("order_products", "В наличии")
        collected_status = reference.get_status_by_type_and_name("order_products", "Собрано")
        assembly_status = reference.get_status_by_type_and_name("orders", "На сборку")
        if in_stock_status is None or assembly_status is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не найдены статусы «В наличии»/«На сборку»")

        # Готовые к отгрузке сейчас: «В наличии» + уже «Собрано» — они остаются в заказе.
        collectable_status_ids = {s.status_id for s in (in_stock_status, collected_status) if s is not None}
        items = list(order.items)
        kept_items = [i for i in items if i.order_item_status_id in collectable_status_ids]
        rest_items = [i for i in items if i.order_item_status_id not in collectable_status_ids]

        if not kept_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет товаров «В наличии»/«Собрано» для сборки")
        if not rest_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нечего разделять: все товары готовы к сборке")

        # Дубль заказа со статусом исходного — в него уходит «остаток» (ожидаемые + отменённые).
        new_order = Order(
            order_establishment_id=order.order_establishment_id,
            order_method_id=order.order_method_id,
            order_sub_method=order.order_sub_method,
            order_contact_method=order.order_contact_method,
            order_customer=order.order_customer,
            order_info=order.order_info,
            order_status_id=order.order_status_id,
            order_owner_user_id=current_user["user_id"],
        )
        self.db.add(new_order)
        self.db.flush()

        for item in rest_items:
            self.db.add(
                OrderItem(
                    order_item_order_id=new_order.order_id,
                    order_item_product_id=item.order_item_product_id,
                    order_item_name=item.order_item_name,
                    order_item_article=item.order_item_article,
                    order_item_quantity=item.order_item_quantity,
                    order_item_price=item.order_item_price,
                    order_item_status_id=item.order_item_status_id,
                    order_item_supplier=item.order_item_supplier,
                    order_item_note=item.order_item_note,
                    order_item_source_establishment_id=item.order_item_source_establishment_id,
                    order_item_destination_establishment_id=item.order_item_destination_establishment_id,
                    order_item_currency_id=item.order_item_currency_id,
                    order_item_checkpoint_started=item.order_item_checkpoint_started,
                    order_item_checkpoint_completed=item.order_item_checkpoint_completed,
                    order_item_owner_user_id=current_user["user_id"],
                )
            )

        new_message = Message(
            message_type="order",
            message_owner_user_id=current_user["user_id"],
            message_order_id=new_order.order_id,
        )
        self.db.add(new_message)

        # Убираем «остаток» из исходного и переводим его в «На сборку».
        rest_item_ids = [i.order_item_id for i in rest_items]
        self.db.execute(delete(OrderItem).where(OrderItem.order_item_id.in_(rest_item_ids)))
        order.order_status_id = assembly_status.status_id

        original_id = order.order_id
        new_order_id = new_order.order_id
        moved_count = len(rest_items)
        kept_count = len(kept_items)

        self.db.commit()
        new_message_id = new_message.message_id

        # Realtime + delta-sync: переотдаём карточки обоих заказов.
        notify_order_changed(self.db, original_id)
        notify_order_changed(self.db, new_order_id)

        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=original_id,
            event_type=EVENT_TYPE_ORDER_UPDATE,
            event_payload={"action": "split", "new_order_id": new_order_id, "moved_items": moved_count, "kept_items": kept_count},
        )

        result_original = serialize_order(self.repository.get_by_id(original_id))
        result_new = serialize_order(self.repository.get_by_id(new_order_id))
        result_new["message_id"] = new_message_id
        return {"order": result_original, "new_order": result_new}

    def _resolve_item_route(self, status_name: str | None, source_establishment_id: int | None, destination_establishment_id: int | None) -> tuple[int | None, int | None]:
        if status_name != "Перемещение":
            return source_establishment_id, destination_establishment_id

        if source_establishment_id is None or destination_establishment_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для статуса 'Перемещение' нужно указать 'Откуда' и 'Куда'")
        if source_establishment_id == destination_establishment_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для перемещения точки 'Откуда' и 'Куда' не должны совпадать")

        get_establishment_or_404(self.db, source_establishment_id)
        get_establishment_or_404(self.db, destination_establishment_id)
        return source_establishment_id, destination_establishment_id


def list_orders(db: Session, current_user: dict, *, page: int = 1, page_size: int = 20, status_ids: list[int] | None = None, method_ids: list[int] | None = None, establishment_ids: list[int] | None = None, search: str | None = None, date_from: date | None = None, date_to: date | None = None) -> dict:
    return OrderService(db).list_orders(current_user, page=page, page_size=page_size, status_ids=status_ids, method_ids=method_ids, establishment_ids=establishment_ids, search=search, date_from=date_from, date_to=date_to)


def get_order(db: Session, order_id: int, current_user: dict) -> dict:
    return serialize_order(OrderService(db).get_accessible_order_or_404(order_id, current_user))


def create_order(db: Session, payload: OrderCreatePayload, current_user: dict) -> dict:
    return OrderService(db).create_order(payload, current_user)


def update_order_status(db: Session, order_id: int, payload: OrderStatusUpdatePayload, current_user: dict) -> dict:
    return OrderService(db).update_order_status(order_id, payload, current_user)


def update_order(db: Session, order_id: int, payload: OrderUpdatePayload, current_user: dict) -> dict:
    return OrderService(db).update_order(order_id, payload, current_user)


def split_order(db: Session, order_id: int, current_user: dict) -> dict:
    return OrderService(db).split_order(order_id, current_user)


def delete_order(db: Session, order_id: int, current_user: dict) -> None:
    OrderService(db).delete_order(order_id, current_user)


def list_order_comments(db: Session, order_id: int, current_user: dict) -> dict:
    return OrderService(db).list_order_comments(order_id, current_user)


def get_order_history(db: Session, order_id: int, current_user: dict) -> dict:
    return OrderService(db).get_order_history(order_id, current_user)


def add_order_comment(db: Session, order_id: int, payload: OrderCommentCreatePayload, current_user: dict, *, enforce_access: bool = True) -> dict:
    return OrderService(db).add_order_comment(order_id, payload, current_user, enforce_access=enforce_access)


def update_order_comment(db: Session, order_id: int, comment_id: int, payload: OrderCommentUpdatePayload, current_user: dict) -> dict:
    return OrderService(db).update_order_comment(order_id, comment_id, payload, current_user)


def delete_order_comment(db: Session, order_id: int, comment_id: int, current_user: dict) -> None:
    OrderService(db).delete_order_comment(order_id, comment_id, current_user)