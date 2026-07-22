"""add order sales channels (канал продаж)

Revision ID: 20260722_000037
Revises: 20260712_000036
Create Date: 2026-07-22 00:00:37

Канал продаж (Розница/Опт/Дроп) — редактируемый справочник order_sales_channels,
плюс строковое значение на заказе (orders.order_sales_channel) и клиенте
(contacts.contact_sales_channel). Значения справочника засеиваются приложением
(ensure_seed_data), миграция создаёт только схему.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260722_000037"
down_revision = "20260712_000036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_sales_channels"):
        op.create_table(
            "order_sales_channels",
            sa.Column("order_sales_channel_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("order_sales_channel_name", sa.String(length=255), nullable=False),
            sa.Column("order_sales_channel_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("order_sales_channel_created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["order_sales_channel_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("order_sales_channel_id"),
            sa.UniqueConstraint("order_sales_channel_name", name="uq_order_sales_channels_name"),
        )
        op.create_index("ix_osc_id", "order_sales_channels", ["order_sales_channel_id"])
        op.create_index("ix_osc_owner", "order_sales_channels", ["order_sales_channel_owner_user_id"])

    if inspector.has_table("orders"):
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "order_sales_channel" not in columns:
            op.add_column("orders", sa.Column("order_sales_channel", sa.String(length=50), nullable=True))

    if inspector.has_table("contacts"):
        columns = {column["name"] for column in inspector.get_columns("contacts")}
        if "contact_sales_channel" not in columns:
            op.add_column("contacts", sa.Column("contact_sales_channel", sa.String(length=50), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("contacts"):
        columns = {column["name"] for column in inspector.get_columns("contacts")}
        if "contact_sales_channel" in columns:
            op.drop_column("contacts", "contact_sales_channel")

    if inspector.has_table("orders"):
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "order_sales_channel" in columns:
            op.drop_column("orders", "order_sales_channel")

    if inspector.has_table("order_sales_channels"):
        op.drop_index("ix_osc_owner", table_name="order_sales_channels")
        op.drop_index("ix_osc_id", table_name="order_sales_channels")
        op.drop_table("order_sales_channels")
