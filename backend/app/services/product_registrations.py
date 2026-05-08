import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_PRODUCT_REGISTRATION, EVENT_TYPE_PRODUCT_REGISTRATION_CREATE, EVENT_TYPE_PRODUCT_REGISTRATION_UPDATE
from app.repositories.messages import MessageRepository
from app.repositories.product_registrations import ProductRegistrationRepository
from app.schemas.common import build_pagination
from app.schemas.product_registrations import ProductRegistrationCreatePayload, ProductRegistrationStatusUpdatePayload
from app.services.contacts import save_supplier_contact
from app.services.audit import log_audit_event
from app.services.domain_common import get_default_currency_or_400, get_default_status_or_400, get_establishment_or_404, get_status_or_404, resolve_product_snapshot
from app.services.push_notifications import send_push_notification_event
from app.services.serializers import serialize_product_registration


logger = logging.getLogger("app.product_registrations")


class ProductRegistrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProductRegistrationRepository(db)
        self.message_repository = MessageRepository(db)

    def get_product_registration_or_404(self, product_registration_id: int):
        row = self.repository.get_by_id(product_registration_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приемка не найдена")
        return row

    def list_product_registrations(self, *, page: int = 1, page_size: int = 20) -> dict:
        rows, total = self.repository.list(page=page, page_size=page_size)
        return {"items": [serialize_product_registration(item) for item in rows], "pagination": build_pagination(page, page_size, total)}

    def create_product_registration(self, payload: ProductRegistrationCreatePayload, current_user: dict) -> dict:
        get_establishment_or_404(self.db, payload.product_registration_establishment_id)
        status_row = get_status_or_404(self.db, payload.product_registration_status_id, expected_type="product_registration") if payload.product_registration_status_id else get_default_status_or_400(self.db, status_type="product_registration")
        default_currency = get_default_currency_or_400(self.db)
        items = []
        for item in payload.items:
            product_row, article, name, cost = resolve_product_snapshot(
                self.db,
                current_user=current_user,
                product_id=item.product_id,
                product_article=item.product_article,
                product_name=item.product_name,
                product_cost_usd=item.product_registration_item_cost,
            )
            items.append(
                {
                    "product_registration_item_product_id": product_row.product_id,
                    "product_registration_item_name": name,
                    "product_registration_item_article": article,
                    "product_registration_item_quantity": item.product_registration_item_quantity,
                    "product_registration_item_cost": cost,
                    "product_registration_item_currency_id": item.product_registration_item_currency_id or default_currency.currency_id,
                    "product_registration_item_owner_user_id": current_user["user_id"],
                }
            )
        row = self.repository.create(
            {
                "product_registration_establishment_id": payload.product_registration_establishment_id,
                "product_registration_supplier": payload.product_registration_supplier.strip(),
                "product_registration_status_id": status_row.status_id,
                "product_registration_owner_user_id": current_user["user_id"],
            },
            items,
        )
        if payload.save_contact:
            save_supplier_contact(self.db, supplier_name=payload.product_registration_supplier, current_user=current_user)
        message = self.message_repository.create(
            {
                "message_type": "product_registration",
                "message_text": payload.message_text.strip() if payload.message_text else None,
                "message_owner_user_id": current_user["user_id"],
                "message_product_registration_id": row.product_registration_id,
            }
        )
        log_audit_event(self.db, actor_user_id=current_user["user_id"], entity_type=ENTITY_TYPE_PRODUCT_REGISTRATION, entity_id=row.product_registration_id, event_type=EVENT_TYPE_PRODUCT_REGISTRATION_CREATE, event_payload={"message_id": message.message_id, "items_count": len(items)})
        result = serialize_product_registration(row)
        result["message_id"] = message.message_id
        try:
            send_push_notification_event(
                self.db,
                excluded_user_id=current_user["user_id"],
                message_type="product_registration",
                sender_name=f"{current_user['user_second_name']} {current_user['user_first_name']}".strip() or current_user["user_login"],
                message_text=payload.message_text,
                entity_id=row.product_registration_id,
            )
        except Exception:
            logger.exception(
                "push.dispatch_failed",
                extra={
                    "event_type": "push.dispatch_failed",
                    "entity_type": "product_registration",
                    "product_registration_id": row.product_registration_id,
                    "user_id": current_user["user_id"],
                },
            )
        return result

    def update_product_registration_status(self, product_registration_id: int, payload: ProductRegistrationStatusUpdatePayload, current_user: dict) -> dict:
        row = self.get_product_registration_or_404(product_registration_id)
        status_row = get_status_or_404(self.db, payload.product_registration_status_id, expected_type="product_registration")
        row = self.repository.update(row, {"product_registration_status_id": status_row.status_id})
        log_audit_event(self.db, actor_user_id=current_user["user_id"], entity_type=ENTITY_TYPE_PRODUCT_REGISTRATION, entity_id=row.product_registration_id, event_type=EVENT_TYPE_PRODUCT_REGISTRATION_UPDATE, event_payload={"product_registration_status_id": status_row.status_id})
        return serialize_product_registration(row)


def list_product_registrations(db: Session, *, page: int = 1, page_size: int = 20) -> dict:
    return ProductRegistrationService(db).list_product_registrations(page=page, page_size=page_size)


def get_product_registration(db: Session, product_registration_id: int) -> dict:
    return serialize_product_registration(ProductRegistrationService(db).get_product_registration_or_404(product_registration_id))


def create_product_registration(db: Session, payload: ProductRegistrationCreatePayload, current_user: dict) -> dict:
    return ProductRegistrationService(db).create_product_registration(payload, current_user)


def update_product_registration_status(db: Session, product_registration_id: int, payload: ProductRegistrationStatusUpdatePayload, current_user: dict) -> dict:
    return ProductRegistrationService(db).update_product_registration_status(product_registration_id, payload, current_user)