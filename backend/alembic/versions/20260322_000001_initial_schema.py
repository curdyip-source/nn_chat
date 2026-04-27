"""initial schema

Revision ID: 20260322_000001
Revises:
Create Date: 2026-03-22 00:00:01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260322_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("user_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_login", sa.String(length=100), nullable=False),
            sa.Column("user_password", sa.Text(), nullable=False),
            sa.Column("user_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("user_active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("user_first_name", sa.String(length=100), nullable=False),
            sa.Column("user_second_name", sa.String(length=100), nullable=False),
            sa.Column("user_age", sa.Integer(), nullable=False),
            sa.Column("user_address", sa.Text(), nullable=False),
            sa.Column("user_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("user_age >= 0", name="ck_users_user_age_non_negative"),
            sa.UniqueConstraint("user_login", name="uq_users_user_login"),
        )

    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_user_id" not in user_indexes:
        op.create_index("ix_users_user_id", "users", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("users"):
        user_indexes = {index["name"] for index in inspector.get_indexes("users")}
        if "ix_users_user_id" in user_indexes:
            op.drop_index("ix_users_user_id", table_name="users")
        op.drop_table("users")