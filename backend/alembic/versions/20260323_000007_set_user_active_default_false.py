"""set user active default false

Revision ID: 20260323_000007
Revises: 20260323_000006
Create Date: 2026-03-23 00:00:07

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260323_000007"
down_revision = "20260323_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "user_active" in columns:
        op.alter_column("users", "user_active", server_default=sa.false(), existing_type=sa.Boolean(), existing_nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "user_active" in columns:
        op.alter_column("users", "user_active", server_default=sa.true(), existing_type=sa.Boolean(), existing_nullable=False)