from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit_types import ENTITY_TYPE_DOCUMENT, EVENT_TYPE_DOCUMENT_CREATE, EVENT_TYPE_DOCUMENT_UPDATE
from app.repositories.documents import DocumentRepository
from app.schemas.common import build_pagination, model_to_dict
from app.schemas.documents import DocumentCreatePayload, DocumentUpdatePayload
from app.services.audit import log_audit_event
from app.services.serializers import serialize_document


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DocumentRepository(db)

    def get_document_or_404(self, document_id: int):
        row = self.repository.get_by_id(document_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
        return row

    def list_documents(self, *, current_user: dict, kind: str | None, status_value: str | None, page: int, page_size: int) -> dict:
        rows, total = self.repository.list_for_user(
            user_id=current_user["user_id"],
            is_admin=current_user["user_admin"],
            kind=kind,
            status=status_value,
            page=page,
            page_size=page_size,
        )
        return {
            "items": [serialize_document(row) for row in rows],
            "pagination": build_pagination(page, page_size, total),
            "filters": {
                "document_kind": kind,
                "document_status": status_value,
            },
        }

    def create_document(self, payload: DocumentCreatePayload, current_user: dict) -> dict:
        row = self.repository.create(
            {
                "document_owner_user_id": current_user["user_id"],
                "document_kind": payload.document_kind,
                "document_original_filename": payload.document_original_filename,
                "document_mime_type": payload.document_mime_type,
                "document_storage_key": payload.document_storage_key,
                "document_status": "pending",
                "document_note": payload.document_note,
                "document_size_bytes": payload.document_size_bytes,
            }
        )
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_DOCUMENT,
            entity_id=row.document_id,
            event_type=EVENT_TYPE_DOCUMENT_CREATE,
            event_payload={"document_kind": row.document_kind, "document_status": row.document_status},
        )
        return serialize_document(row)

    def update_document(self, document_id: int, payload: DocumentUpdatePayload, current_user: dict) -> dict:
        if not current_user["user_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Обновлять статус документа может только администратор")
        row = self.get_document_or_404(document_id)
        data = model_to_dict(payload)
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")
        if "document_status" in data:
            data["document_verified_at"] = datetime.utcnow() if data["document_status"] == "verified" else None
            data["document_verified_by_user_id"] = current_user["user_id"] if data["document_status"] == "verified" else None
        row = self.repository.update(row, data)
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_DOCUMENT,
            entity_id=row.document_id,
            event_type=EVENT_TYPE_DOCUMENT_UPDATE,
            event_payload={"changed_fields": sorted(data.keys()), "document_status": row.document_status},
        )
        return serialize_document(row)


def list_documents(db: Session, *, current_user: dict, kind: str | None, status_value: str | None, page: int, page_size: int) -> dict:
    return DocumentService(db).list_documents(current_user=current_user, kind=kind, status_value=status_value, page=page, page_size=page_size)


def create_document(db: Session, payload: DocumentCreatePayload, current_user: dict) -> dict:
    return DocumentService(db).create_document(payload, current_user)


def update_document(db: Session, document_id: int, payload: DocumentUpdatePayload, current_user: dict) -> dict:
    return DocumentService(db).update_document(document_id, payload, current_user)