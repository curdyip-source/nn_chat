from __future__ import annotations

import re

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.reference_data import Currency, Establishment, OrderMethod, Product, Status


def _split_product_search_tokens(search: str) -> list[str]:
    return [token for token in re.split(r"\s+", search.strip()) if token]


class ReferenceDataRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_establishments(self) -> list[Establishment]:
        return self.db.query(Establishment).options(joinedload(Establishment.owner)).order_by(Establishment.establishment_name.asc(), Establishment.establishment_id.asc()).all()

    def list_order_methods(self) -> list[OrderMethod]:
        return self.db.query(OrderMethod).options(joinedload(OrderMethod.owner)).order_by(OrderMethod.order_method_name.asc(), OrderMethod.order_method_id.asc()).all()

    def list_statuses(self, *, status_type: str | None = None) -> list[Status]:
        query = self.db.query(Status).options(joinedload(Status.owner))
        if status_type:
            query = query.filter(Status.status_type == status_type)
        return query.order_by(Status.status_type.asc(), Status.status_id.asc()).all()

    def list_currencies(self) -> list[Currency]:
        return self.db.query(Currency).options(joinedload(Currency.owner)).order_by(Currency.currency_name.asc(), Currency.currency_id.asc()).all()

    def get_establishment(self, establishment_id: int) -> Establishment | None:
        return self.db.query(Establishment).options(joinedload(Establishment.owner)).filter(Establishment.establishment_id == establishment_id).first()

    def get_establishment_by_name(self, establishment_name: str) -> Establishment | None:
        return self.db.query(Establishment).options(joinedload(Establishment.owner)).filter(Establishment.establishment_name == establishment_name).first()

    def get_order_method(self, order_method_id: int) -> OrderMethod | None:
        return self.db.query(OrderMethod).options(joinedload(OrderMethod.owner)).filter(OrderMethod.order_method_id == order_method_id).first()

    def get_order_method_by_name(self, order_method_name: str) -> OrderMethod | None:
        return self.db.query(OrderMethod).options(joinedload(OrderMethod.owner)).filter(OrderMethod.order_method_name == order_method_name).first()

    def get_status(self, status_id: int) -> Status | None:
        return self.db.query(Status).options(joinedload(Status.owner)).filter(Status.status_id == status_id).first()

    def get_currency(self, currency_id: int) -> Currency | None:
        return self.db.query(Currency).options(joinedload(Currency.owner)).filter(Currency.currency_id == currency_id).first()

    def get_status_by_type_and_name(self, status_type: str, status_name: str) -> Status | None:
        return (
            self.db.query(Status)
            .options(joinedload(Status.owner))
            .filter(Status.status_type == status_type, Status.status_status == status_name)
            .first()
        )

    def get_currency_by_name(self, currency_name: str) -> Currency | None:
        return self.db.query(Currency).options(joinedload(Currency.owner)).filter(Currency.currency_name == currency_name).first()

    def create_establishment(self, data: dict) -> Establishment:
        row = Establishment(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_establishment(row.establishment_id)

    def create_order_method(self, data: dict) -> OrderMethod:
        row = OrderMethod(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_order_method(row.order_method_id)

    def create_status(self, data: dict) -> Status:
        row = Status(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_status(row.status_id)

    def create_currency(self, data: dict) -> Currency:
        row = Currency(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_currency(row.currency_id)

    def update_row(self, row, data: dict):
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return row


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.query(Product).options(joinedload(Product.owner)).filter(Product.product_id == product_id).first()

    def get_by_article(self, product_article: str) -> Product | None:
        return self.db.query(Product).options(joinedload(Product.owner)).filter(Product.product_article == product_article).first()

    def find_by_exact_name(self, product_name: str) -> list[Product]:
        normalized = product_name.strip().lower()
        return (
            self.db.query(Product)
            .options(joinedload(Product.owner))
            .filter(func.lower(func.trim(Product.product_name)) == normalized)
            .order_by(Product.product_id)
            .all()
        )

    def list(self, *, search: str | None = None, page: int = 1, page_size: int = 20, sort_by: str = "product_id", sort_order: str = "desc") -> tuple[list[Product], int]:
        query = self.db.query(Product).options(joinedload(Product.owner))
        if search:
            tokens = _split_product_search_tokens(search)
            for token in tokens:
                like_value = f"%{token}%"
                query = query.filter(or_(Product.product_article.ilike(like_value), Product.product_name.ilike(like_value)))

        order_mapping = {
            "product_id": Product.product_id,
            "product_article": Product.product_article,
            "product_name": Product.product_name,
            "product_cost_usd": Product.product_cost_usd,
            "product_created_at": Product.product_created_at,
        }
        order_column = order_mapping.get(sort_by, Product.product_id)
        order_fn = desc if sort_order == "desc" else asc
        total = query.count()
        items = (
            query.order_by(order_fn(order_column), order_fn(Product.product_id))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, data: dict) -> Product:
        row = Product(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.product_id)

    def update(self, row: Product, data: dict) -> Product:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.product_id)

    def delete(self, row: Product) -> None:
        self.db.delete(row)
        self.db.commit()