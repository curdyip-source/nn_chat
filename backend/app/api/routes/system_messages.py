from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.system_messages import SystemMessageCreatePayload
from app.services.system_messages import (
    acknowledge_system_message,
    create_system_message,
    get_system_message_receipts,
    list_pending_system_messages,
    list_system_messages,
)

router = APIRouter(tags=["system-messages"])


@router.post("/admin/system-messages", status_code=201)
def create_system_message_route(
    payload: SystemMessageCreatePayload,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": create_system_message(db, payload, current_user)}


@router.get("/admin/system-messages")
def list_system_messages_route(_: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return list_system_messages(db)


@router.get("/admin/system-messages/{message_id}/receipts")
def get_system_message_receipts_route(message_id: int, _: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return get_system_message_receipts(db, message_id)


@router.get("/system-messages/pending")
def list_pending_system_messages_route(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return list_pending_system_messages(db, current_user["user_id"])


@router.post("/system-messages/{message_id}/ack")
def acknowledge_system_message_route(message_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return acknowledge_system_message(db, message_id, current_user["user_id"])
