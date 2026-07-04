from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session, joinedload

from app.models.product_registrations import ProductRegistration, ProductRegistrationItem


class ProductRegistrationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return self.db.query(ProductRegistration).options(
            joinedload(ProductRegistration.establishment),
            joinedload(ProductRegistration.status),
            joinedload(ProductRegistration.owner),
            joinedload(ProductRegistration.items),
        )

    def get_by_id(self, product_registration_id: int) -> ProductRegistration | None:
        return self._base_query().filter(ProductRegistration.product_registration_id == product_registration_id).first()

    def list(self, *, page: int = 1, page_size: int = 20, scoped_establishment_ids: set[int] | None = None) -> tuple[list[ProductRegistration], int]:
        query = self._base_query()
        # Ось B: не-админ видит приёмки строго доступных складов.
        if scoped_establishment_ids is not None:
            query = query.filter(ProductRegistration.product_registration_establishment_id.in_(scoped_establishment_ids))
        total = query.count()
        items = (
            query.order_by(ProductRegistration.product_registration_created_at.desc(), ProductRegistration.product_registration_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, data: dict, items: list[dict]) -> ProductRegistration:
        row = ProductRegistration(**data)
        self.db.add(row)
        self.db.flush()
        for item in items:
            self.db.add(ProductRegistrationItem(**item, product_registration_item_product_registration_id=row.product_registration_id))
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.product_registration_id)

    def update(self, row: ProductRegistration, data: dict) -> ProductRegistration:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.product_registration_id)

    def update_with_items(self, row: ProductRegistration, data: dict, items: list[dict]) -> ProductRegistration:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.execute(
            delete(ProductRegistrationItem).where(
                ProductRegistrationItem.product_registration_item_product_registration_id == row.product_registration_id
            )
        )
        self.db.flush()
        for item in items:
            self.db.add(ProductRegistrationItem(**item, product_registration_item_product_registration_id=row.product_registration_id))
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.product_registration_id)