from sqlalchemy.orm import Session, joinedload

from app.models.documents import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, document_id: int) -> Document | None:
        return (
            self.db.query(Document)
            .options(joinedload(Document.owner), joinedload(Document.verified_by))
            .filter(Document.document_id == document_id)
            .first()
        )

    def list_for_user(self, *, user_id: int, is_admin: bool, kind: str | None, status: str | None, page: int, page_size: int) -> tuple[list[Document], int]:
        query = self.db.query(Document).options(joinedload(Document.owner), joinedload(Document.verified_by))
        if not is_admin:
            query = query.filter(Document.document_owner_user_id == user_id)
        if kind:
            query = query.filter(Document.document_kind == kind)
        if status:
            query = query.filter(Document.document_status == status)

        total = query.count()
        items = (
            query.order_by(Document.document_created_at.desc(), Document.document_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, data: dict) -> Document:
        row = Document(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.document_id)

    def update(self, row: Document, data: dict) -> Document:
        for field_name, field_value in data.items():
            setattr(row, field_name, field_value)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.document_id)