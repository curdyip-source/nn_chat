"""rename order item new status

Revision ID: 20260510_000020
Revises: 20260508_000019
Create Date: 2026-05-10 00:00:20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260510_000020"
down_revision = "20260508_000019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("statuses"):
        return

    statuses_table = sa.table(
        "statuses",
        sa.column("status_id", sa.BigInteger()),
        sa.column("status_type", sa.String(length=100)),
        sa.column("status_status", sa.String(length=255)),
        sa.column("status_color", sa.String(length=50)),
    )

    legacy_status_id = bind.execute(
        sa.select(statuses_table.c.status_id).where(
            statuses_table.c.status_type == "order_products",
            statuses_table.c.status_status == "Новый",
        )
    ).scalar_one_or_none()
    replacement_status_id = bind.execute(
        sa.select(statuses_table.c.status_id).where(
            statuses_table.c.status_type == "order_products",
            statuses_table.c.status_status == "Не обработан",
        )
    ).scalar_one_or_none()

    if replacement_status_id is None and legacy_status_id is not None:
        bind.execute(
            statuses_table.update()
            .where(statuses_table.c.status_id == legacy_status_id)
            .values(status_status="Не обработан", status_color="gray")
        )
        return

    if replacement_status_id is not None:
        bind.execute(
            statuses_table.update()
            .where(statuses_table.c.status_id == replacement_status_id)
            .values(status_color="gray")
        )

    if legacy_status_id is None or replacement_status_id is None or not inspector.has_table("order_items"):
        return

    order_items_table = sa.table(
        "order_items",
        sa.column("order_item_status_id", sa.BigInteger()),
    )
    bind.execute(
        order_items_table.update()
        .where(order_items_table.c.order_item_status_id == legacy_status_id)
        .values(order_item_status_id=replacement_status_id)
    )
    bind.execute(statuses_table.delete().where(statuses_table.c.status_id == legacy_status_id))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("statuses"):
        return

    statuses_table = sa.table(
        "statuses",
        sa.column("status_id", sa.BigInteger()),
        sa.column("status_type", sa.String(length=100)),
        sa.column("status_status", sa.String(length=255)),
        sa.column("status_color", sa.String(length=50)),
    )

    legacy_status_id = bind.execute(
        sa.select(statuses_table.c.status_id).where(
            statuses_table.c.status_type == "order_products",
            statuses_table.c.status_status == "Новый",
        )
    ).scalar_one_or_none()
    replacement_status_id = bind.execute(
        sa.select(statuses_table.c.status_id).where(
            statuses_table.c.status_type == "order_products",
            statuses_table.c.status_status == "Не обработан",
        )
    ).scalar_one_or_none()

    if legacy_status_id is None and replacement_status_id is not None:
        bind.execute(
            statuses_table.update()
            .where(statuses_table.c.status_id == replacement_status_id)
            .values(status_status="Новый", status_color="orange")
        )
        return

    if legacy_status_id is not None:
        bind.execute(
            statuses_table.update()
            .where(statuses_table.c.status_id == legacy_status_id)
            .values(status_color="orange")
        )

    if legacy_status_id is None or replacement_status_id is None or not inspector.has_table("order_items"):
        return

    order_items_table = sa.table(
        "order_items",
        sa.column("order_item_status_id", sa.BigInteger()),
    )
    bind.execute(
        order_items_table.update()
        .where(order_items_table.c.order_item_status_id == replacement_status_id)
        .values(order_item_status_id=legacy_status_id)
    )
    bind.execute(statuses_table.delete().where(statuses_table.c.status_id == replacement_status_id))