from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.inventories import Inventory
from app.models.messages import Message, MessageAttachment
from app.models.orders import Order
from app.models.product_registrations import ProductRegistration


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return self.db.query(Message).options(
            joinedload(Message.owner),
            joinedload(Message.attachments),
            joinedload(Message.order).joinedload(Order.status),
            joinedload(Message.order).joinedload(Order.establishment),
            joinedload(Message.order).joinedload(Order.order_method),
            joinedload(Message.order).joinedload(Order.owner),
            joinedload(Message.order).joinedload(Order.items),
            joinedload(Message.inventory).joinedload(Inventory.status),
            joinedload(Message.inventory).joinedload(Inventory.establishment),
            joinedload(Message.inventory).joinedload(Inventory.owner),
            joinedload(Message.inventory).joinedload(Inventory.items),
            joinedload(Message.product_registration).joinedload(ProductRegistration.status),
            joinedload(Message.product_registration).joinedload(ProductRegistration.establishment),
            joinedload(Message.product_registration).joinedload(ProductRegistration.owner),
            joinedload(Message.product_registration).joinedload(ProductRegistration.items),
        )

    def get_by_id(self, message_id: int) -> Message | None:
        return (
            self._base_query()
            .filter(Message.message_id == message_id, Message.message_deleted_at.is_(None))
            .first()
        )

    def list(self, *, before_message_id: int | None = None, page: int = 1, page_size: int = 50) -> tuple[list[Message], int]:
        query = self._base_query().filter(Message.message_deleted_at.is_(None))
        if before_message_id is not None:
            query = query.filter(Message.message_id < before_message_id)
        total = query.count()
        items = (
            query.order_by(Message.message_created_at.desc(), Message.message_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def list_changes(
        self, *, since_updated_at: datetime | None, since_message_id: int | None, limit: int
    ) -> list[Message]:
        """Rows changed since the (updated_at, message_id) cursor, oldest change first.

        On the initial sync (no cursor) tombstones are skipped — a client that never saw a
        message does not need to learn it was deleted. With a cursor, deleted rows are included
        so the client can drop them.
        """
        query = self._base_query()
        if since_updated_at is None or since_message_id is None:
            query = query.filter(Message.message_deleted_at.is_(None))
        else:
            query = query.filter(
                or_(
                    Message.message_updated_at > since_updated_at,
                    and_(
                        Message.message_updated_at == since_updated_at,
                        Message.message_id > since_message_id,
                    ),
                )
            )
        return (
            query.order_by(Message.message_updated_at.asc(), Message.message_id.asc())
            .limit(limit)
            .all()
        )

    def get_by_ids(self, message_ids: list[int]) -> list[Message]:
        if not message_ids:
            return []
        # populate_existing() forces a refresh of identity-map objects (and their eager-loaded
        # relationships) so a card serialized right after its order/inventory/registration changed
        # reflects the new status/items rather than a value cached earlier in this session.
        return (
            self._base_query()
            .populate_existing()
            .filter(Message.message_id.in_(message_ids))
            .all()
        )

    def _touch(self, predicate) -> list[int]:
        rows = self.db.query(Message.message_id).filter(predicate, Message.message_deleted_at.is_(None)).all()
        ids = [row[0] for row in rows]
        if ids:
            self.db.query(Message).filter(Message.message_id.in_(ids)).update(
                {Message.message_updated_at: func.now()}, synchronize_session=False
            )
            self.db.commit()
        return ids

    def touch_for_order(self, order_id: int) -> list[int]:
        return self._touch(Message.message_order_id == order_id)

    def touch_for_inventory(self, inventory_id: int) -> list[int]:
        return self._touch(Message.message_inventory_id == inventory_id)

    def touch_for_product_registration(self, product_registration_id: int) -> list[int]:
        return self._touch(Message.message_product_registration_id == product_registration_id)

    def create(self, data: dict, attachments: list[dict] | None = None) -> Message:
        row = Message(**data)
        self.db.add(row)
        self.db.flush()
        for attachment in attachments or []:
            self.db.add(MessageAttachment(**attachment, attachment_message_id=row.message_id))
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.message_id)

    def update(self, row: Message, data: dict) -> Message:
        for key, value in data.items():
            setattr(row, key, value)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.message_id)

    def delete(self, row: Message) -> None:
        # Soft delete so delta-sync can ship a tombstone; onupdate bumps message_updated_at.
        row.message_deleted_at = func.now()
        self.db.add(row)
        self.db.commit()