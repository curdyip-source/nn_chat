"""add order contact method

Revision ID: 20260617_000024
Revises: 20260522_000023
Create Date: 2026-06-17 00:00:24

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260617_000024"
down_revision = "20260522_000023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("orders"):
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    if "order_contact_method" not in columns:
        op.add_column("orders", sa.Column("order_contact_method", sa.String(length=50), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("orders"):
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    if "order_contact_method" in columns:
        op.drop_column("orders", "order_contact_method")
