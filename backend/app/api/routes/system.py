from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import SYSTEM_PUSH_LOGINS
from app.core.database import get_database_info, get_db
from app.dependencies.auth import get_current_user, require_admin
from app.services.push_notifications import send_system_push
from app.services.users import get_setup_status

router = APIRouter()


class SystemPushPayload(BaseModel):
    """Служебный пуш всем устройствам (прайс обновился и т.п.)."""
    title: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=300)
    event_type: str = Field(default="system", min_length=1, max_length=50)


@router.get("/health/live")
def live_health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready_health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not ready") from error
    return {"status": "ok", "database": "ok"}


@router.get("/setup-status")
def setup_status(db: Session = Depends(get_db)) -> dict:
    return get_setup_status(db)


@router.post("/notifications/system")
def send_system_notification(
    payload: SystemPushPayload,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Пуш «от системы» всем устройствам. Слать может админ или сервисный
    пользователь из SYSTEM_PUSH_LOGINS (прайс шлёт «прайс обновлён»)."""
    if not current_user["user_admin"] and current_user["user_login"] not in SYSTEM_PUSH_LOGINS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для системного уведомления")
    delivered = send_system_push(
        db,
        sender_user_id=current_user["user_id"],
        title=payload.title.strip(),
        body=payload.body.strip(),
        event_type=payload.event_type.strip(),
    )
    return {"delivered": delivered}


@router.get("/db-info")
def db_info(_: dict = Depends(require_admin)) -> dict:
    return get_database_info()