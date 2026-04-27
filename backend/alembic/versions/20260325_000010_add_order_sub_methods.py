"""add order sub methods

Revision ID: 20260325_000010
Revises: 20260324_000009
Create Date: 2026-03-25 00:00:10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260325_000010"
down_revision = "20260324_000009"
branch_labels = None
depends_on = None


AVITO_SUB_METHODS = ["Авито", "СДЭК", "Яндекс", "5Post", "Почта"]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("order_methods"):
        order_method_columns = {column["name"] for column in inspector.get_columns("order_methods")}
        if "order_method_sub_methods" not in order_method_columns:
            op.add_column("order_methods", sa.Column("order_method_sub_methods", sa.JSON(), nullable=True))

        order_methods_table = sa.table(
            "order_methods",
            sa.column("order_method_name", sa.String(length=255)),
            sa.column("order_method_sub_methods", sa.JSON()),
        )
        existing_names = {
            row[0]
            for row in bind.execute(sa.select(order_methods_table.c.order_method_name))
        }
        if "Авито" in existing_names:
            bind.execute(
                order_methods_table.update()
                .where(order_methods_table.c.order_method_name == "Авито")
                .values(order_method_sub_methods=AVITO_SUB_METHODS)
            )
        else:
            bind.execute(
                order_methods_table.insert().values(
                    order_method_name="Авито",
                    order_method_sub_methods=AVITO_SUB_METHODS,
                )
            )

    if inspector.has_table("orders"):
        order_columns = {column["name"] for column in inspector.get_columns("orders")}
        if "order_sub_method" not in order_columns:
            op.add_column("orders", sa.Column("order_sub_method", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("orders"):
        order_columns = {column["name"] for column in inspector.get_columns("orders")}
        if "order_sub_method" in order_columns:
            op.drop_column("orders", "order_sub_method")

    if inspector.has_table("order_methods"):
        order_methods_table = sa.table(
            "order_methods",
            sa.column("order_method_name", sa.String(length=255)),
        )
        bind.execute(order_methods_table.delete().where(order_methods_table.c.order_method_name == "Авито"))

        order_method_columns = {column["name"] for column in inspector.get_columns("order_methods")}
        if "order_method_sub_methods" in order_method_columns:
            op.drop_column("order_methods", "order_method_sub_methods")