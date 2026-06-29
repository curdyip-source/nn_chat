"""add idempotency_keys table

Revision ID: 20260629_000029
Revises: 20260627_000028
Create Date: 2026-06-29 00:00:29

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260629_000029"
down_revision = "20260627_000028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("idempotency_keys"):
        return

    op.create_table(
        "idempotency_keys",
        sa.Column("idempotency_key_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("idempotency_key_value", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key_user_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key_method", sa.String(length=10), nullable=False),
        sa.Column("idempotency_key_path", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key_status_code", sa.Integer(), nullable=False),
        sa.Column("idempotency_key_response", sa.Text(), nullable=False),
        sa.Column("idempotency_key_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_key_id"),
    )
    op.create_index("ix_idempotency_keys_idempotency_key_id", "idempotency_keys", ["idempotency_key_id"])
    op.create_index("ix_idempotency_keys_idempotency_key_value", "idempotency_keys", ["idempotency_key_value"], unique=True)
    op.create_index("ix_idempotency_keys_idempotency_key_user_id", "idempotency_keys", ["idempotency_key_user_id"])
    op.create_index("ix_idempotency_keys_idempotency_key_created_at", "idempotency_keys", ["idempotency_key_created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("idempotency_keys"):
        return

    op.drop_index("ix_idempotency_keys_idempotency_key_created_at", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_idempotency_key_user_id", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_idempotency_key_value", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_idempotency_key_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
