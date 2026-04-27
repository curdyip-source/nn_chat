"""add order item routes and checkpoints

Revision ID: 20260407_000014
Revises: 20260330_000013
Create Date: 2026-04-07 00:00:14

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260407_000014"
down_revision = "20260330_000013"
branch_labels = None
depends_on = None


ORDER_PRODUCT_STATUSES = [
    ("Перемещение", "blue"),
    ("Заказ", "orange"),
    ("В наличии", "green"),
    ("Отгружено", "blue"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("statuses"):
        statuses_table = sa.table(
            "statuses",
            sa.column("status_id", sa.BigInteger()),
            sa.column("status_type", sa.String(length=100)),
            sa.column("status_status", sa.String(length=255)),
            sa.column("status_color", sa.String(length=50)),
        )
        existing_statuses = {
            (row.status_type, row.status_status)
            for row in bind.execute(sa.select(statuses_table.c.status_type, statuses_table.c.status_status))
        }
        for status_name, status_color in ORDER_PRODUCT_STATUSES:
            key = ("order_products", status_name)
            if key in existing_statuses:
                bind.execute(
                    statuses_table.update()
                    .where(
                        statuses_table.c.status_type == "order_products",
                        statuses_table.c.status_status == status_name,
                    )
                    .values(status_color=status_color)
                )
            else:
                bind.execute(
                    statuses_table.insert().values(
                        status_type="order_products",
                        status_status=status_name,
                        status_color=status_color,
                    )
                )

    if not inspector.has_table("order_items"):
        return

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_source_establishment_id" not in columns:
        op.add_column("order_items", sa.Column("order_item_source_establishment_id", sa.BigInteger(), nullable=True))
    if "order_item_destination_establishment_id" not in columns:
        op.add_column("order_items", sa.Column("order_item_destination_establishment_id", sa.BigInteger(), nullable=True))
    if "order_item_checkpoint_started" not in columns:
        op.add_column("order_items", sa.Column("order_item_checkpoint_started", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if "order_item_checkpoint_completed" not in columns:
        op.add_column("order_items", sa.Column("order_item_checkpoint_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    indexes = {index["name"] for index in inspector.get_indexes("order_items")}
    if "ix_order_items_order_item_source_establishment_id" not in indexes:
        op.create_index("ix_order_items_order_item_source_establishment_id", "order_items", ["order_item_source_establishment_id"], unique=False)
    if "ix_order_items_order_item_destination_establishment_id" not in indexes:
        op.create_index("ix_order_items_order_item_destination_establishment_id", "order_items", ["order_item_destination_establishment_id"], unique=False)

    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("order_items")}
    if "fk_order_items_source_establishment_id_establishments" not in fk_names:
        op.create_foreign_key(
            "fk_order_items_source_establishment_id_establishments",
            "order_items",
            "establishments",
            ["order_item_source_establishment_id"],
            ["establishment_id"],
            ondelete="SET NULL",
        )
    if "fk_order_items_destination_establishment_id_establishments" not in fk_names:
        op.create_foreign_key(
            "fk_order_items_destination_establishment_id_establishments",
            "order_items",
            "establishments",
            ["order_item_destination_establishment_id"],
            ["establishment_id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("statuses"):
        statuses_table = sa.table(
            "statuses",
            sa.column("status_type", sa.String(length=100)),
            sa.column("status_status", sa.String(length=255)),
        )
        for status_name, _ in ORDER_PRODUCT_STATUSES:
            bind.execute(
                statuses_table.delete().where(
                    statuses_table.c.status_type == "order_products",
                    statuses_table.c.status_status == status_name,
                )
            )

    if not inspector.has_table("order_items"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("order_items")}
    if "ix_order_items_order_item_source_establishment_id" in indexes:
        op.drop_index("ix_order_items_order_item_source_establishment_id", table_name="order_items")
    if "ix_order_items_order_item_destination_establishment_id" in indexes:
        op.drop_index("ix_order_items_order_item_destination_establishment_id", table_name="order_items")

    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("order_items")}
    if "fk_order_items_source_establishment_id_establishments" in fk_names:
        op.drop_constraint("fk_order_items_source_establishment_id_establishments", "order_items", type_="foreignkey")
    if "fk_order_items_destination_establishment_id_establishments" in fk_names:
        op.drop_constraint("fk_order_items_destination_establishment_id_establishments", "order_items", type_="foreignkey")

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_checkpoint_completed" in columns:
        op.drop_column("order_items", "order_item_checkpoint_completed")
    if "order_item_checkpoint_started" in columns:
        op.drop_column("order_items", "order_item_checkpoint_started")
    if "order_item_destination_establishment_id" in columns:
        op.drop_column("order_items", "order_item_destination_establishment_id")
    if "order_item_source_establishment_id" in columns:
        op.drop_column("order_items", "order_item_source_establishment_id")
