"""drop finance_periods (месяц больше не закрывается — просто фильтр по дате)

Revision ID: 20260923_000047
Revises: 20260923_000046
Create Date: 2026-09-23 00:00:47

Механизм закрытия/открытия месяца оказался лишней сложностью — «Финансы»
работают как обычный фильтр по месяцу без блокировки правок, расходы и
себестоимость редактируются в любой момент.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260923_000047"
down_revision = "20260923_000046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("finance_periods"):
        op.drop_index("ix_finance_periods_month", table_name="finance_periods")
        op.drop_index("ix_finance_periods_id", table_name="finance_periods")
        op.drop_table("finance_periods")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("finance_periods"):
        op.create_table(
            "finance_periods",
            sa.Column("finance_period_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("finance_period_month", sa.Date(), nullable=False),
            sa.Column("finance_period_status", sa.String(length=10), server_default="open", nullable=False),
            sa.Column("finance_period_closed_by_user_id", sa.BigInteger(), nullable=True),
            sa.Column("finance_period_closed_at", sa.DateTime(), nullable=True),
            sa.Column("finance_period_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["finance_period_closed_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("finance_period_id"),
            sa.UniqueConstraint("finance_period_month", name="uq_finance_periods_month"),
        )
        op.create_index("ix_finance_periods_id", "finance_periods", ["finance_period_id"])
        op.create_index("ix_finance_periods_month", "finance_periods", ["finance_period_month"])
