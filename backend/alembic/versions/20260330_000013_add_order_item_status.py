"""add order item status

Revision ID: 20260330_000013
Revises: 20260330_000012
Create Date: 2026-03-30 00:00:13

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260330_000013"
down_revision = "20260330_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_items") or not inspector.has_table("statuses"):
        return

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_status_id" not in columns:
        op.add_column("order_items", sa.Column("order_item_status_id", sa.BigInteger(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("order_items")}
    if "ix_order_items_order_item_status_id" not in indexes:
        op.create_index("ix_order_items_order_item_status_id", "order_items", ["order_item_status_id"], unique=False)

    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("order_items")}
    if "fk_order_items_order_item_status_id_statuses" not in fk_names:
        op.create_foreign_key(
            "fk_order_items_order_item_status_id_statuses",
            "order_items",
            "statuses",
            ["order_item_status_id"],
            ["status_id"],
            ondelete="SET NULL",
        )

    statuses_table = sa.table(
        "statuses",
        sa.column("status_id", sa.BigInteger()),
        sa.column("status_type", sa.String(length=100)),
        sa.column("status_status", sa.String(length=255)),
    )
    default_status_id = bind.execute(
        sa.select(statuses_table.c.status_id).where(
            statuses_table.c.status_type == "order_products",
            statuses_table.c.status_status == "Новый",
        )
    ).scalar_one_or_none()

    if default_status_id is not None:
        order_items_table = sa.table(
            "order_items",
            sa.column("order_item_status_id", sa.BigInteger()),
        )
        bind.execute(
            order_items_table.update()
            .where(order_items_table.c.order_item_status_id.is_(None))
            .values(order_item_status_id=default_status_id)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("order_items"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("order_items")}
    if "ix_order_items_order_item_status_id" in indexes:
        op.drop_index("ix_order_items_order_item_status_id", table_name="order_items")

    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("order_items")}
    if "fk_order_items_order_item_status_id_statuses" in fk_names:
        op.drop_constraint("fk_order_items_order_item_status_id_statuses", "order_items", type_="foreignkey")

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_status_id" in columns:
        op.drop_column("order_items", "order_item_status_id")