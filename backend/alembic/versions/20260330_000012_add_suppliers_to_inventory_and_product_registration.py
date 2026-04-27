"""add suppliers to inventory and product registration

Revision ID: 20260330_000012
Revises: 20260330_000011
Create Date: 2026-03-30 00:00:12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260330_000012"
down_revision = "20260330_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("inventories"):
        inventory_columns = {column["name"] for column in inspector.get_columns("inventories")}
        if "inventory_supplier" not in inventory_columns:
            op.add_column("inventories", sa.Column("inventory_supplier", sa.String(length=255), nullable=True))

    if inspector.has_table("product_registrations"):
        product_registration_columns = {column["name"] for column in inspector.get_columns("product_registrations")}
        if "product_registration_supplier" not in product_registration_columns:
            op.add_column("product_registrations", sa.Column("product_registration_supplier", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("product_registrations"):
        product_registration_columns = {column["name"] for column in inspector.get_columns("product_registrations")}
        if "product_registration_supplier" in product_registration_columns:
            op.drop_column("product_registrations", "product_registration_supplier")

    if inspector.has_table("inventories"):
        inventory_columns = {column["name"] for column in inspector.get_columns("inventories")}
        if "inventory_supplier" in inventory_columns:
            op.drop_column("inventories", "inventory_supplier")