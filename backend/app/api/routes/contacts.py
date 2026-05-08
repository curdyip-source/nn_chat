from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services.contacts import list_contacts

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("")
def get_contacts(
    _: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    contact_type: str = Query(pattern="^(buyer|supplier)$"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_contacts(db, contact_type=contact_type, search=search, page=page, page_size=page_size)