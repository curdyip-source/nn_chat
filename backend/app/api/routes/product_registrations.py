from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.product_registrations import ProductRegistrationCreatePayload, ProductRegistrationStatusUpdatePayload, ProductRegistrationUpdatePayload
from app.services.product_registrations import create_product_registration, get_product_registration, list_product_registrations, update_product_registration, update_product_registration_status

router = APIRouter(prefix="/product-registrations", tags=["product-registrations"])


@router.get("")
def get_product_registrations(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)) -> dict:
    return list_product_registrations(db, current_user, page=page, page_size=page_size)


@router.get("/{product_registration_id}")
def get_product_registration_route(product_registration_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": get_product_registration(db, product_registration_id, current_user)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product_registration_route(payload: ProductRegistrationCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_product_registration(db, payload, current_user)}


@router.put("/{product_registration_id}")
def update_product_registration_route(product_registration_id: int, payload: ProductRegistrationUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_product_registration(db, product_registration_id, payload, current_user)}


@router.put("/{product_registration_id}/status")
def update_product_registration_status_route(product_registration_id: int, payload: ProductRegistrationStatusUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_product_registration_status(db, product_registration_id, payload, current_user)}