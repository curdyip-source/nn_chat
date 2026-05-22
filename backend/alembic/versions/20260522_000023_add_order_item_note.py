"""add order item note

Revision ID: 20260522_000023
Revises: 20260515_000022
Create Date: 2026-05-22 00:00:23

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260522_000023"
down_revision = "20260515_000022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_items"):
        return

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_note" not in columns:
        op.add_column("order_items", sa.Column("order_item_note", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_items"):
        return

    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_note" in columns:
        op.drop_column("order_items", "order_item_note")