"""add finance expense categories, expenses and periods

Revision ID: 20260923_000046
Revises: 20260923_000045
Create Date: 2026-09-23 00:00:46

Финансовый учёт, шаг 2: редактируемый справочник категорий расходов,
сами расходы (зарплаты/налоги/прочее — привязаны к месяцу) и таблица
закрытия месяца (finance_periods), которая блокирует правки расходов
за уже закрытый период.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260923_000046"
down_revision = "20260923_000045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("finance_expense_categories"):
        op.create_table(
            "finance_expense_categories",
            sa.Column("finance_expense_category_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("finance_expense_category_name", sa.String(length=255), nullable=False),
            sa.Column("finance_expense_category_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("finance_expense_category_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["finance_expense_category_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("finance_expense_category_id"),
            sa.UniqueConstraint("finance_expense_category_name", name="uq_finance_expense_categories_name"),
        )
        op.create_index("ix_finance_expense_categories_id", "finance_expense_categories", ["finance_expense_category_id"])
        op.create_index("ix_finance_expense_categories_owner", "finance_expense_categories", ["finance_expense_category_owner_user_id"])

    if not inspector.has_table("finance_expenses"):
        op.create_table(
            "finance_expenses",
            sa.Column("finance_expense_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("finance_expense_category_id", sa.BigInteger(), nullable=False),
            sa.Column("finance_expense_period", sa.Date(), nullable=False),
            sa.Column("finance_expense_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("finance_expense_note", sa.String(length=500), nullable=True),
            sa.Column("finance_expense_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("finance_expense_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["finance_expense_category_id"], ["finance_expense_categories.finance_expense_category_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["finance_expense_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("finance_expense_id"),
        )
        op.create_index("ix_finance_expenses_id", "finance_expenses", ["finance_expense_id"])
        op.create_index("ix_finance_expenses_category", "finance_expenses", ["finance_expense_category_id"])
        op.create_index("ix_finance_expenses_period", "finance_expenses", ["finance_expense_period"])
        op.create_index("ix_finance_expenses_owner", "finance_expenses", ["finance_expense_owner_user_id"])

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


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("finance_periods"):
        op.drop_index("ix_finance_periods_month", table_name="finance_periods")
        op.drop_index("ix_finance_periods_id", table_name="finance_periods")
        op.drop_table("finance_periods")

    if inspector.has_table("finance_expenses"):
        op.drop_index("ix_finance_expenses_owner", table_name="finance_expenses")
        op.drop_index("ix_finance_expenses_period", table_name="finance_expenses")
        op.drop_index("ix_finance_expenses_category", table_name="finance_expenses")
        op.drop_index("ix_finance_expenses_id", table_name="finance_expenses")
        op.drop_table("finance_expenses")

    if inspector.has_table("finance_expense_categories"):
        op.drop_index("ix_finance_expense_categories_owner", table_name="finance_expense_categories")
        op.drop_index("ix_finance_expense_categories_id", table_name="finance_expense_categories")
        op.drop_table("finance_expense_categories")
