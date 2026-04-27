from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_database_info, get_db
from app.dependencies.auth import require_admin
from app.services.users import get_setup_status

router = APIRouter()


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


@router.get("/db-info")
def db_info(_: dict = Depends(require_admin)) -> dict:
    return get_database_info()