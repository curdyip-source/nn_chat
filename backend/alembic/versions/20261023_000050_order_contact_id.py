"""orders.order_contact_id — привязка заказа к покупателю по ключу, а не по имени

Revision ID: 20261023_000050
Revises: 20261023_000049
Create Date: 2026-10-23 00:00:50

Покупатель связывался с заказами по совпадению order_customer == contact_name, а
одинаковых имён много («Александр»): в карточку попадали чужие заказы, а
автозаполнение СДЭК брало данные чужого клиента. Теперь — явный FK. Старые
заказы не привязываем (решение владельца: покупателей в базе почти нет).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261023_000050"
down_revision = "20261023_000049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("orders"):
        return
    columns = {column["name"] for column in inspector.get_columns("orders")}
    if "order_contact_id" not in columns:
        op.add_column("orders", sa.Column("order_contact_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            "fk_orders_order_contact_id_contacts",
            "orders",
            "contacts",
            ["order_contact_id"],
            ["contact_id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_orders_order_contact_id", "orders", ["order_contact_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("orders"):
        return
    columns = {column["name"] for column in inspector.get_columns("orders")}
    if "order_contact_id" in columns:
        op.drop_index("ix_orders_order_contact_id", table_name="orders")
        op.drop_constraint("fk_orders_order_contact_id_contacts", "orders", type_="foreignkey")
        op.drop_column("orders", "order_contact_id")
