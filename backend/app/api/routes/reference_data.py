from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.reference_data import CurrencyPayload, EstablishmentPayload, OrderMethodPayload, StatusPayload
from app.services.reference_data import (
    create_currency,
    create_establishment,
    create_order_method,
    create_status,
    get_reference_data,
    list_currencies,
    list_establishments,
    list_order_methods,
    list_statuses,
    update_currency,
    update_establishment,
    update_order_method,
    update_status,
)

router = APIRouter(tags=["reference-data"])


@router.get("/reference-data")
def get_reference_data_route(_: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return get_reference_data(db)


@router.get("/establishments")
def get_establishments(_: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return list_establishments(db)


@router.post("/establishments", status_code=status.HTTP_201_CREATED)
def create_establishment_route(payload: EstablishmentPayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": create_establishment(db, payload, current_user)}


@router.put("/establishments/{establishment_id}")
def update_establishment_route(establishment_id: int, payload: EstablishmentPayload, _: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": update_establishment(db, establishment_id, payload)}


@router.get("/order-methods")
def get_order_methods(_: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return list_order_methods(db)


@router.post("/order-methods", status_code=status.HTTP_201_CREATED)
def create_order_method_route(payload: OrderMethodPayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": create_order_method(db, payload, current_user)}


@router.put("/order-methods/{order_method_id}")
def update_order_method_route(order_method_id: int, payload: OrderMethodPayload, _: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": update_order_method(db, order_method_id, payload)}


@router.get("/statuses")
def get_statuses(_: dict = Depends(get_current_user), db: Session = Depends(get_db), status_type: str | None = Query(default=None)) -> dict:
    return list_statuses(db, status_type=status_type)


@router.post("/statuses", status_code=status.HTTP_201_CREATED)
def create_status_route(payload: StatusPayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": create_status(db, payload, current_user)}


@router.put("/statuses/{status_id}")
def update_status_route(status_id: int, payload: StatusPayload, _: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": update_status(db, status_id, payload)}


@router.get("/currencies")
def get_currencies(_: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return list_currencies(db)


@router.post("/currencies", status_code=status.HTTP_201_CREATED)
def create_currency_route(payload: CurrencyPayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": create_currency(db, payload, current_user)}


@router.put("/currencies/{currency_id}")
def update_currency_route(currency_id: int, payload: CurrencyPayload, _: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": update_currency(db, currency_id, payload)}