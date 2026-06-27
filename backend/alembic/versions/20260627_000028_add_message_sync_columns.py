"""add message sync columns

Revision ID: 20260627_000028
Revises: 20260627_000027
Create Date: 2026-06-27 00:00:28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260627_000028"
down_revision = "20260627_000027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("messages"):
        return

    columns = {column["name"] for column in inspector.get_columns("messages")}
    indexes = {index["name"] for index in inspector.get_indexes("messages")}

    if "message_updated_at" not in columns:
        op.add_column(
            "messages",
            sa.Column("message_updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        # Backfill existing rows so they sort by their original creation time, not the migration time.
        op.execute("UPDATE messages SET message_updated_at = message_created_at")
    if "message_deleted_at" not in columns:
        op.add_column("messages", sa.Column("message_deleted_at", sa.DateTime(), nullable=True))
    if "ix_messages_message_updated_at" not in indexes:
        op.create_index("ix_messages_message_updated_at", "messages", ["message_updated_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("messages"):
        return

    columns = {column["name"] for column in inspector.get_columns("messages")}
    indexes = {index["name"] for index in inspector.get_indexes("messages")}

    if "ix_messages_message_updated_at" in indexes:
        op.drop_index("ix_messages_message_updated_at", table_name="messages")
    if "message_deleted_at" in columns:
        op.drop_column("messages", "message_deleted_at")
    if "message_updated_at" in columns:
        op.drop_column("messages", "message_updated_at")
