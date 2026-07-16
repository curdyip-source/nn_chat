from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.orders import OrderCommentCreatePayload, OrderCommentUpdatePayload, OrderCreatePayload, OrderStatusUpdatePayload, OrderUpdatePayload
from app.services.orders import add_order_comment, create_order, delete_order, delete_order_comment, get_order, get_order_history, list_order_comments, list_orders, split_order, update_order, update_order_comment, update_order_status

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
def get_orders(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_id: list[int] | None = Query(default=None),
    method_id: list[int] | None = Query(default=None),
    establishment_id: list[int] | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict:
    return list_orders(db, current_user, page=page, page_size=page_size, status_ids=status_id, method_ids=method_id, establishment_ids=establishment_id, search=search, date_from=date_from, date_to=date_to)


@router.get("/{order_id}")
def get_order_route(order_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": get_order(db, order_id, current_user)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order_route(payload: OrderCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_order(db, payload, current_user)}


@router.put("/{order_id}")
def update_order_route(order_id: int, payload: OrderUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_order(db, order_id, payload, current_user)}


@router.put("/{order_id}/status")
def update_order_status_route(order_id: int, payload: OrderStatusUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_order_status(db, order_id, payload, current_user)}


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_route(order_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    delete_order(db, order_id, current_user)


@router.post("/{order_id}/split")
def split_order_route(order_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    # Частичная отгрузка: «В наличии»/«Собрано» → этот заказ в «На сборку», остальное → новый заказ-дубль.
    return split_order(db, order_id, current_user)


@router.get("/{order_id}/history")
def get_order_history_route(order_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return get_order_history(db, order_id, current_user)


@router.get("/{order_id}/comments")
def get_order_comments(order_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return list_order_comments(db, order_id, current_user)


@router.post("/{order_id}/comments", status_code=status.HTTP_201_CREATED)
def add_order_comment_route(order_id: int, payload: OrderCommentCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": add_order_comment(db, order_id, payload, current_user)}


@router.put("/{order_id}/comments/{comment_id}")
def update_order_comment_route(order_id: int, comment_id: int, payload: OrderCommentUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_order_comment(db, order_id, comment_id, payload, current_user)}


@router.delete("/{order_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_comment_route(order_id: int, comment_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    delete_order_comment(db, order_id, comment_id, current_user)