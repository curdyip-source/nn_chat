"""order_items: закупочная цена в валюте продажи + фиксатор (раздел «Финансы» приложения)

Revision ID: 20261026_000051
Revises: 20261023_000050
Create Date: 2026-10-26 00:00:51

order_item_purchase_price — закупочная цена ЗА ЕДИНИЦУ в валюте позиции, как её вносят
в приложении (точно, без округления через курс). Параллельно пересчитывается
order_item_cost_usd, чтобы веб-«Финансы» видели те же цифры. NULL — закупка ещё не
внесена (снимок cost_usd из каталога не считается внесённой закупкой).

order_item_cost_locked — «фиксатор»: зафиксированную позицию нельзя править ни в
приложении, ни в вебе, пока фиксатор не снимут.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261026_000051"
down_revision = "20261023_000050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("order_items"):
        return
    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_purchase_price" not in columns:
        op.add_column("order_items", sa.Column("order_item_purchase_price", sa.Numeric(12, 2), nullable=True))
    if "order_item_cost_locked" not in columns:
        op.add_column("order_items", sa.Column("order_item_cost_locked", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "order_item_cost_locked_at" not in columns:
        op.add_column("order_items", sa.Column("order_item_cost_locked_at", sa.DateTime(), nullable=True))
    if "order_item_cost_locked_by_user_id" not in columns:
        op.add_column("order_items", sa.Column("order_item_cost_locked_by_user_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            "fk_order_items_cost_locked_by_user_id_users",
            "order_items",
            "users",
            ["order_item_cost_locked_by_user_id"],
            ["user_id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("order_items"):
        return
    columns = {column["name"] for column in inspector.get_columns("order_items")}
    if "order_item_cost_locked_by_user_id" in columns:
        op.drop_constraint("fk_order_items_cost_locked_by_user_id_users", "order_items", type_="foreignkey")
        op.drop_column("order_items", "order_item_cost_locked_by_user_id")
    for name in ("order_item_cost_locked_at", "order_item_cost_locked", "order_item_purchase_price"):
        if name in columns:
            op.drop_column("order_items", name)
