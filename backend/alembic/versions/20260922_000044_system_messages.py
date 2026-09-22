"""system_messages + system_message_recipients (блокирующие системные сообщения из «Админки»)

Revision ID: 20260922_000044
Revises: 20260808_000043
Create Date: 2026-09-22 00:00:44
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260922_000044"
down_revision = "20260808_000043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("system_messages"):
        op.create_table(
            "system_messages",
            sa.Column("system_message_id", sa.BigInteger(), primary_key=True),
            sa.Column("system_message_text", sa.Text(), nullable=False),
            sa.Column("system_message_important", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("system_message_created_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column("system_message_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["system_message_created_by_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_system_messages_created_by_user_id", "system_messages", ["system_message_created_by_user_id"])

    if not inspector.has_table("system_message_recipients"):
        op.create_table(
            "system_message_recipients",
            sa.Column("system_message_recipient_id", sa.BigInteger(), primary_key=True),
            sa.Column("system_message_recipient_message_id", sa.BigInteger(), nullable=False),
            sa.Column("system_message_recipient_user_id", sa.BigInteger(), nullable=False),
            sa.Column("system_message_recipient_acked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["system_message_recipient_message_id"], ["system_messages.system_message_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["system_message_recipient_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.UniqueConstraint("system_message_recipient_message_id", "system_message_recipient_user_id", name="uq_system_message_recipient"),
        )
        op.create_index("ix_system_message_recipients_message_id", "system_message_recipients", ["system_message_recipient_message_id"])
        op.create_index("ix_system_message_recipients_user_id", "system_message_recipients", ["system_message_recipient_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("system_message_recipients"):
        op.drop_table("system_message_recipients")
    if inspector.has_table("system_messages"):
        op.drop_table("system_messages")
