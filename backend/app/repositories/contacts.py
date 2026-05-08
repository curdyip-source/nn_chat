from __future__ import annotations

import re

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.models.contacts import Contact


def _split_contact_search_tokens(search: str) -> list[str]:
    return [token for token in re.split(r"\s+", search.strip()) if token]


class ContactRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        contact_type: str,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Contact], int]:
        query = (
            self.db.query(Contact)
            .options(joinedload(Contact.establishment), joinedload(Contact.order_method), joinedload(Contact.owner))
            .filter(Contact.contact_type == contact_type)
        )

        if search:
            tokens = _split_contact_search_tokens(search)
            for token in tokens:
                like_value = f"%{token}%"
                query = query.filter(or_(Contact.contact_name.ilike(like_value), Contact.contact_info.ilike(like_value)))

        total = query.count()
        items = (
            query.order_by(desc(Contact.contact_created_at), desc(Contact.contact_id))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def find_exact(self, *, data: dict) -> Contact | None:
        return (
            self.db.query(Contact)
            .options(joinedload(Contact.establishment), joinedload(Contact.order_method), joinedload(Contact.owner))
            .filter(
                Contact.contact_type == data["contact_type"],
                Contact.contact_name == data["contact_name"],
                Contact.contact_info == data.get("contact_info"),
                Contact.contact_establishment_id == data.get("contact_establishment_id"),
                Contact.contact_order_method_id == data.get("contact_order_method_id"),
                Contact.contact_order_sub_method == data.get("contact_order_sub_method"),
            )
            .first()
        )

    def get_by_id(self, contact_id: int) -> Contact | None:
        return (
            self.db.query(Contact)
            .options(joinedload(Contact.establishment), joinedload(Contact.order_method), joinedload(Contact.owner))
            .filter(Contact.contact_id == contact_id)
            .first()
        )

    def create(self, data: dict) -> Contact:
        row = Contact(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.get_by_id(row.contact_id)