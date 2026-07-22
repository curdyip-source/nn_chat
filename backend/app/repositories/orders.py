from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, delete, false, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.orders import Order, OrderComment, OrderCommentAttachment, OrderItem
from app.models.reference_data import Currency


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

    def _apply_order_filters(
        self,
        query,
        *,
        status_ids: list[int] | None,
        method_ids: list[int] | None,
        establishment_ids: list[int] | None,
        scoped_full_ids: set[int] | None = None,
        scoped_own_ids: set[int] | None = None,
        scoped_user_id: int | None = None,
        search: str | None,
        date_from: date | None,
        date_to: date | None,
    ):
        # Область видимости (per-warehouse): scoped_full_ids None → без ограничения (админ).
        # Иначе виден заказ, если его склад ∈ full (видны все) ИЛИ (склад ∈ own и владелец=user).
        if scoped_full_ids is not None:
            conditions = []
            if scoped_full_ids:
                conditions.append(Order.order_establishment_id.in_(scoped_full_ids))
            if scoped_own_ids:
                conditions.append(and_(Order.order_establishment_id.in_(scoped_own_ids), Order.order_owner_user_id == scoped_user_id))
            query = query.filter(or_(*conditions) if conditions else false())
        if status_ids:
            query = query.filter(Order.order_status_id.in_(status_ids))
        if method_ids:
            query = query.filter(Order.order_method_id.in_(method_ids))
        if establishment_ids:
            query = query.filter(Order.order_establishment_id.in_(establishment_ids))
        if date_from:
            query = query.filter(Order.order_created_at >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.filter(Order.order_created_at < datetime.combine(date_to + timedelta(days=1), time.min))
        if search:
            stripped = search.strip()
            like_value = f"%{stripped}%"
            conditions = [Order.order_customer.ilike(like_value), Order.order_info.ilike(like_value)]
            # Числовой запрос — ищем ещё и по номеру заказа (order_id).
            if stripped.isdigit():
                conditions.append(Order.order_id == int(stripped))
            query = query.filter(or_(*conditions))
        return query

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status_ids: list[int] | None = None,
        method_ids: list[int] | None = None,
        establishment_ids: list[int] | None = None,
        scoped_full_ids: set[int] | None = None,
        scoped_own_ids: set[int] | None = None,
        scoped_user_id: int | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Order], int]:
        query = self._apply_order_filters(
            self._base_query(),
            status_ids=status_ids,
            method_ids=method_ids,
            establishment_ids=establishment_ids,
            scoped_full_ids=scoped_full_ids,
            scoped_own_ids=scoped_own_ids,
            scoped_user_id=scoped_user_id,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        total = query.count()
        items = (
            query.order_by(Order.order_created_at.desc(), Order.order_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def totals_by_currency(
        self,
        *,
        status_ids: list[int] | None = None,
        method_ids: list[int] | None = None,
        establishment_ids: list[int] | None = None,
        scoped_full_ids: set[int] | None = None,
        scoped_own_ids: set[int] | None = None,
        scoped_user_id: int | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[tuple[int | None, str | None, float]]:
        # Сумма по всем заказам, попавшим под фильтры (без пагинации), сгруппированная по валюте.
        query = (
            self.db.query(
                Currency.currency_id,
                Currency.currency_sign,
                func.coalesce(func.sum(OrderItem.order_item_price * OrderItem.order_item_quantity), 0),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_item_order_id == Order.order_id)
            .outerjoin(Currency, OrderItem.order_item_currency_id == Currency.currency_id)
        )
        query = self._apply_order_filters(
            query,
            status_ids=status_ids,
            method_ids=method_ids,
            establishment_ids=establishment_ids,
            scoped_full_ids=scoped_full_ids,
            scoped_own_ids=scoped_own_ids,
            scoped_user_id=scoped_user_id,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        rows = query.group_by(Currency.currency_id, Currency.currency_sign).all()
        return [(currency_id, currency_sign, float(amount or 0)) for currency_id, currency_sign, amount in rows]

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

    def delete(self, row: Order) -> None:
        # Жёсткое удаление: позиции и комментарии уходят каскадом (relationship
        # cascade="all, delete-orphan"). Карточку-сообщение чата гасим отдельно
        # (мягко, с отвязкой) до вызова — см. OrderService.delete_order.
        self.db.delete(row)
        self.db.commit()

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

    def update_comment(self, row: OrderComment, data: dict) -> OrderComment:
        for key, value in data.items():
            setattr(row, key, value)
        self.db.commit()
        return self.get_comment_by_id(row.order_comment_id)

    def delete_comment(self, row: OrderComment) -> None:
        # Жёсткое удаление: вложения комментария уходят каскадом (FK ondelete=CASCADE +
        # relationship cascade="all, delete-orphan").
        self.db.delete(row)
        self.db.commit()