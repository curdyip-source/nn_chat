"""add user_establishment_roles table

Revision ID: 20260704_000032
Revises: 20260703_000031
Create Date: 2026-07-04 00:00:32

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260704_000032"
down_revision = "20260703_000031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("user_establishment_roles"):
        return

    op.create_table(
        "user_establishment_roles",
        sa.Column("user_establishment_role_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_establishment_role_user_id", sa.BigInteger(), nullable=False),
        sa.Column("user_establishment_role_establishment_id", sa.BigInteger(), nullable=False),
        sa.Column("user_establishment_role_role", sa.String(length=20), nullable=False),
        sa.Column("user_establishment_role_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_establishment_role_user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_establishment_role_establishment_id"], ["establishments.establishment_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_establishment_role_id"),
        sa.UniqueConstraint(
            "user_establishment_role_user_id",
            "user_establishment_role_establishment_id",
            name="uq_user_establishment_role_user_establishment",
        ),
    )
    # Короткие имена индексов — полные (ix_<table>_<column>) превышают лимит Postgres в 63 символа.
    op.create_index("ix_uer_id", "user_establishment_roles", ["user_establishment_role_id"])
    op.create_index("ix_uer_user_id", "user_establishment_roles", ["user_establishment_role_user_id"])
    op.create_index("ix_uer_establishment_id", "user_establishment_roles", ["user_establishment_role_establishment_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("user_establishment_roles"):
        return

    op.drop_index("ix_uer_establishment_id", table_name="user_establishment_roles")
    op.drop_index("ix_uer_user_id", table_name="user_establishment_roles")
    op.drop_index("ix_uer_id", table_name="user_establishment_roles")
    op.drop_table("user_establishment_roles")
