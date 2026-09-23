"""add exchange rates and order item cost snapshot

Revision ID: 20260923_000045
Revises: 20260922_000044
Create Date: 2026-09-23 00:00:45

Финансовый учёт, шаг 1: таблица истории курса USD/RUB (exchange_rates,
источник — ЦБ РФ с возможностью ручной коррекции) и снимок себестоимости
на позиции заказа (order_item_cost_usd/order_item_cost_rate), фиксируемый
на момент создания позиции.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260923_000045"
down_revision = "20260922_000044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("exchange_rates"):
        op.create_table(
            "exchange_rates",
            sa.Column("exchange_rate_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("exchange_rate_date", sa.Date(), nullable=False),
            sa.Column("exchange_rate_value", sa.Numeric(10, 4), nullable=False),
            sa.Column("exchange_rate_source", sa.String(length=20), server_default="cbr", nullable=False),
            sa.Column("exchange_rate_fetched_at", sa.DateTime(), nullable=True),
            sa.Column("exchange_rate_updated_by_user_id", sa.BigInteger(), nullable=True),
            sa.Column("exchange_rate_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["exchange_rate_updated_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("exchange_rate_id"),
            sa.UniqueConstraint("exchange_rate_date", name="uq_exchange_rates_date"),
        )
        op.create_index("ix_exchange_rates_id", "exchange_rates", ["exchange_rate_id"])
        op.create_index("ix_exchange_rates_date", "exchange_rates", ["exchange_rate_date"])

    if inspector.has_table("order_items"):
        columns = {column["name"] for column in inspector.get_columns("order_items")}
        for name, coltype in [
            ("order_item_cost_usd", sa.Numeric(12, 2)),
            ("order_item_cost_rate", sa.Numeric(10, 4)),
            ("order_item_cost_updated_at", sa.DateTime()),
            ("order_item_cost_updated_by_user_id", sa.BigInteger()),
        ]:
            if name not in columns:
                op.add_column("order_items", sa.Column(name, coltype, nullable=True))

        columns = {column["name"] for column in inspector.get_columns("order_items")}
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("order_items")}
        if "order_item_cost_updated_by_user_id" in columns and "fk_order_items_cost_updated_by" not in fk_names:
            op.create_foreign_key(
                "fk_order_items_cost_updated_by",
                "order_items",
                "users",
                ["order_item_cost_updated_by_user_id"],
                ["user_id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("order_items"):
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("order_items")}
        if "fk_order_items_cost_updated_by" in fk_names:
            op.drop_constraint("fk_order_items_cost_updated_by", "order_items", type_="foreignkey")

        columns = {column["name"] for column in inspector.get_columns("order_items")}
        for name in [
            "order_item_cost_updated_by_user_id",
            "order_item_cost_updated_at",
            "order_item_cost_rate",
            "order_item_cost_usd",
        ]:
            if name in columns:
                op.drop_column("order_items", name)

    if inspector.has_table("exchange_rates"):
        op.drop_index("ix_exchange_rates_date", table_name="exchange_rates")
        op.drop_index("ix_exchange_rates_id", table_name="exchange_rates")
        op.drop_table("exchange_rates")
