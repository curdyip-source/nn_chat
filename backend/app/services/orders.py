import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_ORDER, EVENT_TYPE_ORDER_COMMENT_CREATE, EVENT_TYPE_ORDER_CREATE, EVENT_TYPE_ORDER_UPDATE
from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.repositories.messages import MessageRepository
from app.repositories.orders import OrderRepository
from app.schemas.common import build_pagination
from app.schemas.orders import OrderCommentCreatePayload, OrderCreatePayload, OrderStatusUpdatePayload, OrderUpdatePayload
from app.services.contacts import save_buyer_contact_from_order
from app.services.audit import log_audit_event
from app.services.domain_common import get_default_currency_or_400, get_default_status_or_400, get_establishment_or_404, get_order_method_or_404, get_status_or_404, resolve_product_snapshot
from app.services.push_notifications import send_push_notification_event
from app.services.serializers import serialize_order, serialize_order_comment


logger = logging.getLogger("app.orders")


ORDER_AUDIT_FIELDS = (
    "order_establishment_id",
    "order_establishment_name",
    "order_method_id",
    "order_method_name",
    "order_sub_method",
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
    "order_item_source_establishment_id",
    "order_item_source_establishment_name",
    "order_item_destination_establishment_id",
    "order_item_destination_establishment_name",
    "order_item_currency_id",
    "order_item_checkpoint_started",
    "order_item_checkpoint_completed",
)


def _build_order_item_identity(item: dict, sequence: int) -> str:
    if item.get("order_item_product_id") is not None:
        base = f"product:{item['order_item_product_id']}"
    else:
        base = f"manual:{item.get('order_item_article') or ''}:{item.get('order_item_name') or ''}"
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


def _build_order_update_audit_payload(before: dict, after: dict) -> dict:
    return {
        "changed_fields": _build_order_audit_changes(before, after),
        "items": _build_order_item_audit_changes(before.get("items", []), after.get("items", [])),
    }


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

    def list_orders(self, *, page: int = 1, page_size: int = 20) -> dict:
        rows, total = self.repository.list(page=page, page_size=page_size)
        return {"items": [serialize_order(item) for item in rows], "pagination": build_pagination(page, page_size, total)}

    def create_order(self, payload: OrderCreatePayload, current_user: dict) -> dict:
        get_establishment_or_404(self.db, payload.order_establishment_id)
        order_method_row = get_order_method_or_404(self.db, payload.order_method_id)
        available_sub_methods = order_method_row.order_method_sub_methods or []
        normalized_order_sub_method = payload.order_sub_method.strip() if payload.order_sub_method else None
        if available_sub_methods and normalized_order_sub_method is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для выбранного способа заказа нужно указать подспособ")
        if not available_sub_methods and normalized_order_sub_method is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для выбранного способа заказа подспособ не поддерживается")
        if normalized_order_sub_method is not None and normalized_order_sub_method not in available_sub_methods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неизвестный подспособ заказа")
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
            if item_status.status_status != "Заказ":
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
                    "order_item_source_establishment_id": source_establishment_id,
                    "order_item_destination_establishment_id": destination_establishment_id,
                    "order_item_currency_id": item.order_item_currency_id or default_currency.currency_id,
                    "order_item_checkpoint_started": item.order_item_checkpoint_started,
                    "order_item_checkpoint_completed": item.order_item_checkpoint_completed,
                    "order_item_owner_user_id": current_user["user_id"],
                }
            )

        row = self.repository.create(
            {
                "order_establishment_id": payload.order_establishment_id,
                "order_method_id": payload.order_method_id,
                "order_sub_method": normalized_order_sub_method,
                "order_customer": payload.order_customer,
                "order_info": payload.order_info,
                "order_status_id": status_row.status_id,
                "order_owner_user_id": current_user["user_id"],
            },
            items,
        )
        if payload.save_contact:
            save_buyer_contact_from_order(
                self.db,
                order_customer=payload.order_customer,
                order_info=payload.order_info,
                order_establishment_id=payload.order_establishment_id,
                order_method_id=payload.order_method_id,
                order_sub_method=normalized_order_sub_method,
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
        row = self.get_order_or_404(order_id)
        before_snapshot = serialize_order(row)
        get_establishment_or_404(self.db, payload.order_establishment_id)
        order_method_row = get_order_method_or_404(self.db, payload.order_method_id)
        available_sub_methods = order_method_row.order_method_sub_methods or []
        normalized_order_sub_method = payload.order_sub_method.strip() if payload.order_sub_method else None
        if available_sub_methods and normalized_order_sub_method is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для выбранного способа заказа нужно указать подспособ")
        if not available_sub_methods and normalized_order_sub_method is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для выбранного способа заказа подспособ не поддерживается")
        if normalized_order_sub_method is not None and normalized_order_sub_method not in available_sub_methods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неизвестный подспособ заказа")

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
            if item_status.status_status != "Заказ":
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
                "order_customer": payload.order_customer,
                "order_info": payload.order_info,
                "order_status_id": status_row.status_id,
            },
            items,
        )
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=row.order_id,
            event_type=EVENT_TYPE_ORDER_UPDATE,
            event_payload=_build_order_update_audit_payload(before_snapshot, serialize_order(row)),
        )
        return serialize_order(row)

    def update_order_status(self, order_id: int, payload: OrderStatusUpdatePayload, current_user: dict) -> dict:
        row = self.get_order_or_404(order_id)
        before_snapshot = serialize_order(row)
        status_row = get_status_or_404(self.db, payload.order_status_id, expected_type="orders")
        row = self.repository.update(row, {"order_status_id": status_row.status_id})
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_ORDER,
            entity_id=row.order_id,
            event_type=EVENT_TYPE_ORDER_UPDATE,
            event_payload=_build_order_update_audit_payload(before_snapshot, serialize_order(row)),
        )
        return serialize_order(row)

    def list_order_comments(self, order_id: int) -> dict:
        row = self.get_order_or_404(order_id)
        items = sorted(
            row.comments,
            key=lambda item: (item.order_comment_created_at.isoformat() if item.order_comment_created_at else "", item.order_comment_id),
        )
        return {"items": [serialize_order_comment(item) for item in items]}

    def add_order_comment(self, order_id: int, payload: OrderCommentCreatePayload, current_user: dict) -> dict:
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
        return serialize_order_comment(row)

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


def list_orders(db: Session, *, page: int = 1, page_size: int = 20) -> dict:
    return OrderService(db).list_orders(page=page, page_size=page_size)


def get_order(db: Session, order_id: int) -> dict:
    return serialize_order(OrderService(db).get_order_or_404(order_id))


def create_order(db: Session, payload: OrderCreatePayload, current_user: dict) -> dict:
    return OrderService(db).create_order(payload, current_user)


def update_order_status(db: Session, order_id: int, payload: OrderStatusUpdatePayload, current_user: dict) -> dict:
    return OrderService(db).update_order_status(order_id, payload, current_user)


def update_order(db: Session, order_id: int, payload: OrderUpdatePayload, current_user: dict) -> dict:
    return OrderService(db).update_order(order_id, payload, current_user)


def list_order_comments(db: Session, order_id: int) -> dict:
    return OrderService(db).list_order_comments(order_id)


def add_order_comment(db: Session, order_id: int, payload: OrderCommentCreatePayload, current_user: dict) -> dict:
    return OrderService(db).add_order_comment(order_id, payload, current_user)