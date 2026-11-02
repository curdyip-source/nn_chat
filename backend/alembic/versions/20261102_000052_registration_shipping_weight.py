"""Приёмка: стоимость доставки и вес позиции (распределение доставки по весу)

Revision ID: 20261102_000052
Revises: 20261026_000051
Create Date: 2026-11-02 00:00:52

product_registration_shipping_cost / _currency_id — доставка всей приёмки.
product_registration_item_weight — вес ОДНОЙ штуки, кг. Доля доставки на позицию не
хранится: её считает сериализатор, чтобы правка веса сразу меняла себестоимость.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261102_000052"
down_revision = "20261026_000051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("product_registrations"):
        columns = {column["name"] for column in inspector.get_columns("product_registrations")}
        if "product_registration_shipping_cost" not in columns:
            op.add_column("product_registrations", sa.Column("product_registration_shipping_cost", sa.Numeric(12, 2), nullable=True))
        if "product_registration_shipping_currency_id" not in columns:
            op.add_column("product_registrations", sa.Column("product_registration_shipping_currency_id", sa.BigInteger(), nullable=True))
            op.create_foreign_key(
                "fk_product_registrations_shipping_currency_id_currencies",
                "product_registrations",
                "currencies",
                ["product_registration_shipping_currency_id"],
                ["currency_id"],
                ondelete="SET NULL",
            )
    if inspector.has_table("product_registration_items"):
        columns = {column["name"] for column in inspector.get_columns("product_registration_items")}
        if "product_registration_item_weight" not in columns:
            op.add_column("product_registration_items", sa.Column("product_registration_item_weight", sa.Numeric(10, 3), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("product_registration_items"):
        columns = {column["name"] for column in inspector.get_columns("product_registration_items")}
        if "product_registration_item_weight" in columns:
            op.drop_column("product_registration_items", "product_registration_item_weight")
    if inspector.has_table("product_registrations"):
        columns = {column["name"] for column in inspector.get_columns("product_registrations")}
        if "product_registration_shipping_currency_id" in columns:
            op.drop_constraint("fk_product_registrations_shipping_currency_id_currencies", "product_registrations", type_="foreignkey")
            op.drop_column("product_registrations", "product_registration_shipping_currency_id")
        if "product_registration_shipping_cost" in columns:
            op.drop_column("product_registrations", "product_registration_shipping_cost")
