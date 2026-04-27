"""enforce unique statuses

Revision ID: 20260408_000017
Revises: 20260408_000016
Create Date: 2026-04-08 21:15:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260408_000017"
down_revision = "20260408_000016"
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
    )

    duplicate_pairs: list[tuple[int, int]] = []
    canonical_by_key: dict[tuple[str, str], int] = {}
    status_rows = bind.execute(
        sa.select(
            statuses_table.c.status_id,
            statuses_table.c.status_type,
            statuses_table.c.status_status,
        ).order_by(statuses_table.c.status_id.asc())
    )

    for row in status_rows:
        key = (row.status_type, row.status_status)
        canonical_id = canonical_by_key.get(key)
        if canonical_id is None:
            canonical_by_key[key] = row.status_id
            continue
        duplicate_pairs.append((row.status_id, canonical_id))

    if duplicate_pairs:
        if inspector.has_table("orders"):
            orders_table = sa.table(
                "orders",
                sa.column("order_status_id", sa.BigInteger()),
            )
            for duplicate_id, canonical_id in duplicate_pairs:
                bind.execute(
                    orders_table.update()
                    .where(orders_table.c.order_status_id == duplicate_id)
                    .values(order_status_id=canonical_id)
                )

        if inspector.has_table("inventories"):
            inventories_table = sa.table(
                "inventories",
                sa.column("inventory_status_id", sa.BigInteger()),
            )
            for duplicate_id, canonical_id in duplicate_pairs:
                bind.execute(
                    inventories_table.update()
                    .where(inventories_table.c.inventory_status_id == duplicate_id)
                    .values(inventory_status_id=canonical_id)
                )

        if inspector.has_table("product_registrations"):
            product_registrations_table = sa.table(
                "product_registrations",
                sa.column("product_registration_status_id", sa.BigInteger()),
            )
            for duplicate_id, canonical_id in duplicate_pairs:
                bind.execute(
                    product_registrations_table.update()
                    .where(product_registrations_table.c.product_registration_status_id == duplicate_id)
                    .values(product_registration_status_id=canonical_id)
                )

        if inspector.has_table("order_items"):
            order_items_table = sa.table(
                "order_items",
                sa.column("order_item_status_id", sa.BigInteger()),
            )
            for duplicate_id, canonical_id in duplicate_pairs:
                bind.execute(
                    order_items_table.update()
                    .where(order_items_table.c.order_item_status_id == duplicate_id)
                    .values(order_item_status_id=canonical_id)
                )

        duplicate_ids = [duplicate_id for duplicate_id, _ in duplicate_pairs]
        bind.execute(statuses_table.delete().where(statuses_table.c.status_id.in_(duplicate_ids)))

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("statuses")}
    if "uq_statuses_type_name" not in unique_constraints:
        op.create_unique_constraint("uq_statuses_type_name", "statuses", ["status_type", "status_status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("statuses"):
        return

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("statuses")}
    if "uq_statuses_type_name" in unique_constraints:
        op.drop_constraint("uq_statuses_type_name", "statuses", type_="unique")