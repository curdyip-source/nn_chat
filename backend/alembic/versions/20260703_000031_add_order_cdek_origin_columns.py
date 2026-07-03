"""add order cdek origin (sender) columns

Revision ID: 20260703_000031
Revises: 20260703_000030
Create Date: 2026-07-03 00:00:31

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260703_000031"
down_revision = "20260703_000030"
branch_labels = None
depends_on = None


_ORIGIN_COLUMNS = [
    ("order_cdek_from_city_code", sa.Integer()),
    ("order_cdek_from_city_name", sa.String(255)),
    ("order_cdek_shipment_point", sa.String(50)),
    ("order_cdek_shipment_point_address", sa.String(500)),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("orders"):
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    for name, type_ in _ORIGIN_COLUMNS:
        if name not in columns:
            op.add_column("orders", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("orders"):
        return

    columns = {column["name"] for column in inspector.get_columns("orders")}
    for name, _ in reversed(_ORIGIN_COLUMNS):
        if name in columns:
            op.drop_column("orders", name)
