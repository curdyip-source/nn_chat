"""add order item supplier

Revision ID: 20260508_000019
Revises: 20260508_000018
Create Date: 2026-05-08 00:00:19

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260508_000019"
down_revision = "20260508_000018"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("order_items") and "order_item_supplier" not in _column_names(inspector, "order_items"):
        op.add_column("order_items", sa.Column("order_item_supplier", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("order_items") and "order_item_supplier" in _column_names(inspector, "order_items"):
        op.drop_column("order_items", "order_item_supplier")