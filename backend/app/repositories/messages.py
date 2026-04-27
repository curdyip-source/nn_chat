from __future__ import annotations

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
        return self._base_query().filter(Message.message_id == message_id).first()

    def list(self, *, before_message_id: int | None = None, page: int = 1, page_size: int = 50) -> tuple[list[Message], int]:
        query = self._base_query()
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
        self.db.delete(row)
        self.db.commit()