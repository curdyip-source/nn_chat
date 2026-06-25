from __future__ import annotations

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session, joinedload

from app.models.orders import Order, OrderComment, OrderCommentAttachment, OrderItem


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return self.db.query(Order).options(
            joinedload(Order.establishment),
            joinedload(Order.order_method),
            joinedload(Order.status),
            joinedload(Order.owner),
            joinedload(Order.items).joinedload(OrderItem.status),
            joinedload(Order.items).joinedload(OrderItem.source_establishment),
            joinedload(Order.items).joinedload(OrderItem.destination_establishment),
            joinedload(Order.items).joinedload(OrderItem.currency),
            joinedload(Order.comments).joinedload(OrderComment.owner),
            joinedload(Order.comments).joinedload(OrderComment.attachments),
        )

    def get_by_id(self, order_id: int) -> Order | None:
        return self._base_query().filter(Order.order_id == order_id).first()

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status_ids: list[int] | None = None,
        method_ids: list[int] | None = None,
        search: str | None = None,
    ) -> tuple[list[Order], int]:
        query = self._base_query()
        if status_ids:
            query = query.filter(Order.order_status_id.in_(status_ids))
        if method_ids:
            query = query.filter(Order.order_method_id.in_(method_ids))
        if search:
            like_value = f"%{search.strip()}%"
            query = query.filter(
                or_(Order.order_customer.ilike(like_value), Order.order_info.ilike(like_value))
            )
        total = query.count()
        items = (
            query.order_by(Order.order_created_at.desc(), Order.order_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, data: dict, items: list[dict]) -> Order:
        row = Order(**data)
        self.db.add(row)
        self.db.flush()
        for item in items:
            self.db.add(OrderItem(**item, order_item_order_id=row.order_id))
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.order_id)

    def update(self, row: Order, data: dict) -> Order:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.order_id)

    def update_with_items(self, row: Order, data: dict, items: list[dict]) -> Order:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)

        self.db.execute(delete(OrderItem).where(OrderItem.order_item_order_id == row.order_id))
        self.db.flush()
        for item in items:
            self.db.add(OrderItem(**item, order_item_order_id=row.order_id))

        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.order_id)

    def add_comment(self, order_id: int, data: dict, attachments: list[dict] | None = None) -> OrderComment:
        row = OrderComment(**data, order_comment_order_id=order_id)
        self.db.add(row)
        self.db.flush()
        for attachment in attachments or []:
            self.db.add(OrderCommentAttachment(**attachment, attachment_order_comment_id=row.order_comment_id))
        self.db.commit()
        return self.get_comment_by_id(row.order_comment_id)

    def get_comment_by_id(self, order_comment_id: int) -> OrderComment | None:
        return (
            self.db.query(OrderComment)
            .options(joinedload(OrderComment.owner), joinedload(OrderComment.attachments))
            .filter(OrderComment.order_comment_id == order_comment_id)
            .first()
        )