"""add documents

Revision ID: 20260322_000003
Revises: 20260322_000002
Create Date: 2026-03-22 00:00:03

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260322_000003"
down_revision = "20260322_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("documents"):
        op.create_table(
            "documents",
            sa.Column("document_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("document_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("document_verified_by_user_id", sa.BigInteger(), nullable=True),
            sa.Column("document_kind", sa.String(length=100), nullable=False),
            sa.Column("document_original_filename", sa.String(length=255), nullable=False),
            sa.Column("document_mime_type", sa.String(length=150), nullable=False),
            sa.Column("document_storage_key", sa.String(length=255), nullable=False),
            sa.Column("document_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("document_note", sa.Text(), nullable=True),
            sa.Column("document_size_bytes", sa.Integer(), nullable=True),
            sa.Column("document_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("document_verified_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["document_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["document_verified_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.UniqueConstraint("document_storage_key", name="uq_documents_storage_key"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("documents")}
    if "ix_documents_document_id" not in indexes:
        op.create_index("ix_documents_document_id", "documents", ["document_id"], unique=False)
    if "ix_documents_document_owner_user_id" not in indexes:
        op.create_index("ix_documents_document_owner_user_id", "documents", ["document_owner_user_id"], unique=False)
    if "ix_documents_document_verified_by_user_id" not in indexes:
        op.create_index("ix_documents_document_verified_by_user_id", "documents", ["document_verified_by_user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("documents"):
        indexes = {index["name"] for index in inspector.get_indexes("documents")}
        if "ix_documents_document_verified_by_user_id" in indexes:
            op.drop_index("ix_documents_document_verified_by_user_id", table_name="documents")
        if "ix_documents_document_owner_user_id" in indexes:
            op.drop_index("ix_documents_document_owner_user_id", table_name="documents")
        if "ix_documents_document_id" in indexes:
            op.drop_index("ix_documents_document_id", table_name="documents")
        op.drop_table("documents")