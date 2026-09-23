"""add order_item_shipped_at (дата отгрузки, а не дата создания заказа)

Revision ID: 20260923_000048
Revises: 20260923_000047
Create Date: 2026-09-23 00:00:48

«Финансы» фильтровали позиции по дате СОЗДАНИЯ заказа — если заказ оформлен
21-го, а товар реально отгружен 23-го, он не попадал в фильтр за 23-е число.
order_item_shipped_at фиксирует момент перехода статуса позиции в «Отгружено»
и используется для фильтрации/сортировки вместо orders.order_created_at.

Бэкополним уже отгруженные позиции их order_item_created_at — точной даты
отгрузки для них не было, это лучшее доступное приближение, чтобы старые
данные не пропали из свода молча.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260923_000048"
down_revision = "20260923_000047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_items"):
        return

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_shipped_at" not in columns:
        op.add_column("order_items", sa.Column("order_item_shipped_at", sa.DateTime(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("order_items")}
    if "ix_order_items_order_item_shipped_at" not in indexes:
        op.create_index("ix_order_items_order_item_shipped_at", "order_items", ["order_item_shipped_at"])

    if inspector.has_table("statuses"):
        op.execute(
            """
            UPDATE order_items
            SET order_item_shipped_at = order_item_created_at
            FROM statuses
            WHERE order_items.order_item_status_id = statuses.status_id
              AND statuses.status_type = 'order_products'
              AND statuses.status_status = 'Отгружено'
              AND order_items.order_item_shipped_at IS NULL
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("order_items"):
        indexes = {index["name"] for index in inspector.get_indexes("order_items")}
        if "ix_order_items_order_item_shipped_at" in indexes:
            op.drop_index("ix_order_items_order_item_shipped_at", table_name="order_items")

        columns = {column["name"] for column in inspector.get_columns("order_items")}
        if "order_item_shipped_at" in columns:
            op.drop_column("order_items", "order_item_shipped_at")
