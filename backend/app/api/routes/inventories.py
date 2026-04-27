from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.inventories import InventoryCreatePayload, InventoryStatusUpdatePayload
from app.services.inventories import create_inventory, get_inventory, list_inventories, update_inventory_status

router = APIRouter(prefix="/inventories", tags=["inventories"])


@router.get("")
def get_inventories(_: dict = Depends(get_current_user), db: Session = Depends(get_db), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)) -> dict:
    return list_inventories(db, page=page, page_size=page_size)


@router.get("/{inventory_id}")
def get_inventory_route(inventory_id: int, _: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": get_inventory(db, inventory_id)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_inventory_route(payload: InventoryCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_inventory(db, payload, current_user)}


@router.put("/{inventory_id}/status")
def update_inventory_status_route(inventory_id: int, payload: InventoryStatusUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_inventory_status(db, inventory_id, payload, current_user)}