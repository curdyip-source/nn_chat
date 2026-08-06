"""add order payment mark (оплата заказа)

Revision ID: 20260806_000039
Revises: 20260722_000038
Create Date: 2026-08-06 00:00:39

Отметка «Оплачено» на заказе: момент оплаты (NULL = не оплачен) и кто отметил.
Заполняется кнопкой в карточке заказа, снимается там же.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260806_000039"
down_revision = "20260722_000038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("orders"):
        return
    columns = {column["name"] for column in inspector.get_columns("orders")}

    if "order_paid_at" not in columns:
        op.add_column("orders", sa.Column("order_paid_at", sa.DateTime(), nullable=True))
    if "order_paid_by_user_id" not in columns:
        # Ссылку на пользователя объявляем прямо в колонке: ADD COLUMN ... REFERENCES
        # проходит одним стейтментом (и на PostgreSQL, и на SQLite в тестах).
        op.add_column(
            "orders",
            sa.Column(
                "order_paid_by_user_id",
                sa.BigInteger(),
                sa.ForeignKey("users.user_id", ondelete="SET NULL", name="fk_orders_paid_by_user"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("orders"):
        return
    columns = {column["name"] for column in inspector.get_columns("orders")}

    if "order_paid_by_user_id" in columns:
        op.drop_column("orders", "order_paid_by_user_id")
    if "order_paid_at" in columns:
        op.drop_column("orders", "order_paid_at")
