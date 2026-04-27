"""add order comment attachments

Revision ID: 20260408_000016
Revises: 20260408_000015
Create Date: 2026-04-08 00:00:16

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260408_000016"
down_revision = "20260408_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("order_comment_attachments"):
        return

    op.create_table(
        "order_comment_attachments",
        sa.Column("attachment_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("attachment_order_comment_id", sa.BigInteger(), sa.ForeignKey("order_comments.order_comment_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attachment_owner_user_id", sa.BigInteger(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attachment_kind", sa.String(length=50), nullable=False),
        sa.Column("attachment_original_filename", sa.String(length=255), nullable=False),
        sa.Column("attachment_mime_type", sa.String(length=150), nullable=False),
        sa.Column("attachment_storage_key", sa.String(length=255), nullable=False),
        sa.Column("attachment_size_bytes", sa.Integer(), nullable=True),
        sa.Column("attachment_created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_order_comment_attachments_attachment_id", "order_comment_attachments", ["attachment_id"], unique=False)
    op.create_index("ix_order_comment_attachments_attachment_order_comment_id", "order_comment_attachments", ["attachment_order_comment_id"], unique=False)
    op.create_index("ix_order_comment_attachments_attachment_owner_user_id", "order_comment_attachments", ["attachment_owner_user_id"], unique=False)
    op.create_index("ix_order_comment_attachments_attachment_storage_key", "order_comment_attachments", ["attachment_storage_key"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("order_comment_attachments"):
        return
    op.drop_index("ix_order_comment_attachments_attachment_storage_key", table_name="order_comment_attachments")
    op.drop_index("ix_order_comment_attachments_attachment_owner_user_id", table_name="order_comment_attachments")
    op.drop_index("ix_order_comment_attachments_attachment_order_comment_id", table_name="order_comment_attachments")
    op.drop_index("ix_order_comment_attachments_attachment_id", table_name="order_comment_attachments")
    op.drop_table("order_comment_attachments")
