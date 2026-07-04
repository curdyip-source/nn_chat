"""Propagate entity (order/inventory/registration) changes through the chat-card sync channel.

Each card (chat message) embeds its order/inventory/registration with status and items. When one
of those entities changes, we bump the referencing message's updated_at so delta-sync picks it up,
and emit an SSE `updated` event carrying the freshly serialized card so connected clients update
statuses/items instantly.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.messages import MessageRepository
from app.services.message_stream import broker
from app.services.serializers import serialize_message


def _emit_updated(db: Session, message_ids: list[int]) -> None:
    if not message_ids:
        return
    for row in MessageRepository(db).get_by_ids(message_ids):
        broker.publish({"type": "updated", "message": serialize_message(row)})


def notify_order_changed(db: Session, order_id: int) -> None:
    _emit_updated(db, MessageRepository(db).touch_for_order(order_id))


def notify_cards_deleted(message_ids: list[int]) -> None:
    # Карточки уже погашены мягко (tombstone). Публикуем SSE `deleted`, чтобы
    # подключённые клиенты убрали их из ленты сразу (как delete_message).
    for message_id in message_ids:
        broker.publish({"type": "deleted", "message_id": message_id})


def notify_inventory_changed(db: Session, inventory_id: int) -> None:
    _emit_updated(db, MessageRepository(db).touch_for_inventory(inventory_id))


def notify_product_registration_changed(db: Session, product_registration_id: int) -> None:
    _emit_updated(db, MessageRepository(db).touch_for_product_registration(product_registration_id))
