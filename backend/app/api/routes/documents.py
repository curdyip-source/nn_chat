from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.documents import DocumentCreatePayload, DocumentUpdatePayload
from app.services.documents import create_document, list_documents, update_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def get_documents(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    document_kind: str | None = Query(default=None),
    document_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    return list_documents(db, current_user=current_user, kind=document_kind, status_value=document_status, page=page, page_size=page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document_route(payload: DocumentCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_document(db, payload, current_user)}


@router.put("/{document_id}")
def update_document_route(document_id: int, payload: DocumentUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_document(db, document_id, payload, current_user)}