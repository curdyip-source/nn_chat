"""add message attachment assets

Revision ID: 20260408_000015
Revises: 20260407_000014
Create Date: 2026-04-08 00:00:15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260408_000015"
down_revision = "20260407_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("message_attachment_assets"):
        return

    op.create_table(
        "message_attachment_assets",
        sa.Column("attachment_asset_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("attachment_asset_owner_user_id", sa.BigInteger(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attachment_asset_storage_key", sa.String(length=255), nullable=False),
        sa.Column("attachment_asset_original_filename", sa.String(length=255), nullable=False),
        sa.Column("attachment_asset_mime_type", sa.String(length=150), nullable=False),
        sa.Column("attachment_asset_kind", sa.String(length=50), nullable=False),
        sa.Column("attachment_asset_size_bytes", sa.Integer(), nullable=False),
        sa.Column("attachment_asset_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("attachment_asset_created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_message_attachment_assets_attachment_asset_id", "message_attachment_assets", ["attachment_asset_id"], unique=False)
    op.create_index("ix_message_attachment_assets_attachment_asset_owner_user_id", "message_attachment_assets", ["attachment_asset_owner_user_id"], unique=False)
    op.create_index("ix_message_attachment_assets_attachment_asset_storage_key", "message_attachment_assets", ["attachment_asset_storage_key"], unique=True)
    op.create_index("ix_message_attachment_assets_attachment_asset_created_at", "message_attachment_assets", ["attachment_asset_created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("message_attachment_assets"):
        return
    op.drop_index("ix_message_attachment_assets_attachment_asset_created_at", table_name="message_attachment_assets")
    op.drop_index("ix_message_attachment_assets_attachment_asset_storage_key", table_name="message_attachment_assets")
    op.drop_index("ix_message_attachment_assets_attachment_asset_owner_user_id", table_name="message_attachment_assets")
    op.drop_index("ix_message_attachment_assets_attachment_asset_id", table_name="message_attachment_assets")
    op.drop_table("message_attachment_assets")