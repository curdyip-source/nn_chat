from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.messages import MessageCreatePayload, MessageUpdatePayload
from app.services.messages import create_message, delete_message, list_messages, update_message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
def get_messages(
    _: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    before_message_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    return list_messages(db, before_message_id=before_message_id, page=page, page_size=page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_message_route(payload: MessageCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_message(db, payload, current_user)}


@router.put("/{message_id}")
def update_message_route(message_id: int, payload: MessageUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_message(db, message_id, payload, current_user)}


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message_route(message_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    delete_message(db, message_id, current_user)