"""add user active and created at

Revision ID: 20260323_000006
Revises: 20260322_000005
Create Date: 2026-03-23 00:00:06

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260323_000006"
down_revision = "20260322_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "user_active" not in columns:
        op.add_column("users", sa.Column("user_active", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "user_created_at" not in columns:
        op.add_column("users", sa.Column("user_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "user_created_at" in columns:
        op.drop_column("users", "user_created_at")
    if "user_active" in columns:
        op.drop_column("users", "user_active")