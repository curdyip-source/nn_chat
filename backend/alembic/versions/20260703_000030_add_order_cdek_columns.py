"""add order cdek columns

Revision ID: 20260703_000030
Revises: 20260629_000029
Create Date: 2026-07-03 00:00:30

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260703_000030"
down_revision = "20260629_000029"
branch_labels = None
depends_on = None


_CDEK_COLUMNS = [
    ("order_cdek_recipient_name", sa.String(255)),
    ("order_cdek_recipient_phone", sa.String(50)),
    ("order_cdek_city_code", sa.Integer()),
    ("order_cdek_city_name", sa.String(255)),
    ("order_cdek_delivery_mode", sa.String(10)),
    ("order_cdek_pvz_code", sa.String(50)),
    ("order_cdek_pvz_address", sa.String(500)),
    ("order_cdek_delivery_address", sa.String(500)),
    ("order_cdek_uuid", sa.String(64)),
    ("order_cdek_track_number", sa.String(64)),
    ("order_cdek_status", sa.String(100)),
    ("order_cdek_status_updated_at", sa.DateTime()),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("orders"):
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    indexes = {index["name"] for index in inspector.get_indexes("orders")}

    for name, type_ in _CDEK_COLUMNS:
        if name not in columns:
            op.add_column("orders", sa.Column(name, type_, nullable=True))

    if "ix_orders_order_cdek_uuid" not in indexes:
        op.create_index("ix_orders_order_cdek_uuid", "orders", ["order_cdek_uuid"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("orders"):
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    indexes = {index["name"] for index in inspector.get_indexes("orders")}

    if "ix_orders_order_cdek_uuid" in indexes:
        op.drop_index("ix_orders_order_cdek_uuid", table_name="orders")
    for name, _ in reversed(_CDEK_COLUMNS):
        if name in columns:
            op.drop_column("orders", name)
