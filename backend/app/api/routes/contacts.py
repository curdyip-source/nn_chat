from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_section
from app.schemas.contacts import ContactUpdatePayload
from app.services.contacts import delete_contact, get_contact, list_contact_orders, list_contacts, update_contact

router = APIRouter(prefix="/contacts", tags=["contacts"])

# Список нужен и форме заказа (поиск клиента) — на любом входе. Карточка, правка,
# удаление и заказы покупателя — только с разделом «Контрагенты» в СРМ.
require_contacts = require_section("crm", "contacts")


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


@router.get("/{contact_id}")
def get_contact_route(contact_id: int, _: dict = Depends(require_contacts), db: Session = Depends(get_db)) -> dict:
    return {"item": get_contact(db, contact_id)}


@router.put("/{contact_id}")
def update_contact_route(contact_id: int, payload: ContactUpdatePayload, current_user: dict = Depends(require_contacts), db: Session = Depends(get_db)) -> dict:
    return {"item": update_contact(db, contact_id, payload, current_user)}


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact_route(contact_id: int, current_user: dict = Depends(require_contacts), db: Session = Depends(get_db)) -> None:
    delete_contact(db, contact_id, current_user)


@router.get("/{contact_id}/orders")
def contact_orders_route(contact_id: int, current_user: dict = Depends(require_contacts), db: Session = Depends(get_db)) -> dict:
    return list_contact_orders(db, contact_id, current_user)
