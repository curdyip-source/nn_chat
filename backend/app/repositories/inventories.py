from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session, joinedload

from app.models.inventories import Inventory, InventoryItem


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return self.db.query(Inventory).options(
            joinedload(Inventory.establishment),
            joinedload(Inventory.status),
            joinedload(Inventory.owner),
            joinedload(Inventory.items),
        )

    def get_by_id(self, inventory_id: int) -> Inventory | None:
        return self._base_query().filter(Inventory.inventory_id == inventory_id).first()

    def list(self, *, page: int = 1, page_size: int = 20) -> tuple[list[Inventory], int]:
        query = self._base_query()
        total = query.count()
        items = (
            query.order_by(Inventory.inventory_created_at.desc(), Inventory.inventory_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, data: dict, items: list[dict]) -> Inventory:
        row = Inventory(**data)
        self.db.add(row)
        self.db.flush()
        for item in items:
            self.db.add(InventoryItem(**item, inventory_item_inventory_id=row.inventory_id))
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.inventory_id)

    def update(self, row: Inventory, data: dict) -> Inventory:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.inventory_id)

    def update_with_items(self, row: Inventory, data: dict, items: list[dict]) -> Inventory:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.execute(delete(InventoryItem).where(InventoryItem.inventory_item_inventory_id == row.inventory_id))
        self.db.flush()
        for item in items:
            self.db.add(InventoryItem(**item, inventory_item_inventory_id=row.inventory_id))
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.inventory_id)