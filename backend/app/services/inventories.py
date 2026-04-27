import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_INVENTORY, EVENT_TYPE_INVENTORY_CREATE, EVENT_TYPE_INVENTORY_UPDATE
from app.repositories.inventories import InventoryRepository
from app.repositories.messages import MessageRepository
from app.schemas.common import build_pagination
from app.schemas.inventories import InventoryCreatePayload, InventoryStatusUpdatePayload
from app.services.audit import log_audit_event
from app.services.domain_common import get_default_currency_or_400, get_default_status_or_400, get_establishment_or_404, get_status_or_404, resolve_product_snapshot
from app.services.push_notifications import send_push_notification_event
from app.services.serializers import serialize_inventory


logger = logging.getLogger("app.inventories")


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)
        self.message_repository = MessageRepository(db)

    def get_inventory_or_404(self, inventory_id: int):
        row = self.repository.get_by_id(inventory_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инвентаризация не найдена")
        return row

    def list_inventories(self, *, page: int = 1, page_size: int = 20) -> dict:
        rows, total = self.repository.list(page=page, page_size=page_size)
        return {"items": [serialize_inventory(item) for item in rows], "pagination": build_pagination(page, page_size, total)}

    def create_inventory(self, payload: InventoryCreatePayload, current_user: dict) -> dict:
        get_establishment_or_404(self.db, payload.inventory_establishment_id)
        status_row = get_status_or_404(self.db, payload.inventory_status_id, expected_type="inventory") if payload.inventory_status_id else get_default_status_or_400(self.db, status_type="inventory")
        default_currency = get_default_currency_or_400(self.db)
        items = []
        for item in payload.items:
            product_row, article, name, cost = resolve_product_snapshot(
                self.db,
                current_user=current_user,
                product_id=item.product_id,
                product_article=item.product_article,
                product_name=item.product_name,
                product_cost_usd=item.inventory_item_cost,
            )
            items.append(
                {
                    "inventory_item_product_id": product_row.product_id,
                    "inventory_item_name": name,
                    "inventory_item_article": article,
                    "inventory_item_quantity": item.inventory_item_quantity,
                    "inventory_item_cost": cost,
                    "inventory_item_currency_id": item.inventory_item_currency_id or default_currency.currency_id,
                    "inventory_item_owner_user_id": current_user["user_id"],
                }
            )
        row = self.repository.create(
            {
                "inventory_establishment_id": payload.inventory_establishment_id,
                "inventory_supplier": payload.inventory_supplier.strip() if payload.inventory_supplier else None,
                "inventory_status_id": status_row.status_id,
                "inventory_owner_user_id": current_user["user_id"],
            },
            items,
        )
        message = self.message_repository.create(
            {
                "message_type": "inventory",
                "message_text": payload.message_text.strip() if payload.message_text else None,
                "message_owner_user_id": current_user["user_id"],
                "message_inventory_id": row.inventory_id,
            }
        )
        log_audit_event(self.db, actor_user_id=current_user["user_id"], entity_type=ENTITY_TYPE_INVENTORY, entity_id=row.inventory_id, event_type=EVENT_TYPE_INVENTORY_CREATE, event_payload={"message_id": message.message_id, "items_count": len(items)})
        result = serialize_inventory(row)
        result["message_id"] = message.message_id
        try:
            send_push_notification_event(
                self.db,
                excluded_user_id=current_user["user_id"],
                message_type="inventory",
                sender_name=f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"],
                message_text=payload.message_text,
                entity_id=row.inventory_id,
            )
        except Exception:
            logger.exception(
                "push.dispatch_failed",
                extra={
                    "event_type": "push.dispatch_failed",
                    "entity_type": "inventory",
                    "inventory_id": row.inventory_id,
                    "user_id": current_user["user_id"],
                },
            )
        return result

    def update_inventory_status(self, inventory_id: int, payload: InventoryStatusUpdatePayload, current_user: dict) -> dict:
        row = self.get_inventory_or_404(inventory_id)
        status_row = get_status_or_404(self.db, payload.inventory_status_id, expected_type="inventory")
        row = self.repository.update(row, {"inventory_status_id": status_row.status_id})
        log_audit_event(self.db, actor_user_id=current_user["user_id"], entity_type=ENTITY_TYPE_INVENTORY, entity_id=row.inventory_id, event_type=EVENT_TYPE_INVENTORY_UPDATE, event_payload={"inventory_status_id": status_row.status_id})
        return serialize_inventory(row)


def list_inventories(db: Session, *, page: int = 1, page_size: int = 20) -> dict:
    return InventoryService(db).list_inventories(page=page, page_size=page_size)


def get_inventory(db: Session, inventory_id: int) -> dict:
    return serialize_inventory(InventoryService(db).get_inventory_or_404(inventory_id))


def create_inventory(db: Session, payload: InventoryCreatePayload, current_user: dict) -> dict:
    return InventoryService(db).create_inventory(payload, current_user)


def update_inventory_status(db: Session, inventory_id: int, payload: InventoryStatusUpdatePayload, current_user: dict) -> dict:
    return InventoryService(db).update_inventory_status(inventory_id, payload, current_user)