"""normalize required statuses

Revision ID: 20260510_000021
Revises: 20260510_000020
Create Date: 2026-05-10 00:00:21

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260510_000021"
down_revision = "20260510_000020"
branch_labels = None
depends_on = None


REQUIRED_STATUSES = [
    ("orders", "Новый", "orange"),
    ("orders", "В обработке", "blue"),
    ("orders", "На сборку", "blue"),
    ("orders", "Собран", "green"),
    ("orders", "Выполнен", "green"),
    ("orders", "Отменен", "red"),
    ("inventory", "Новый", "orange"),
    ("inventory", "В обработке", "blue"),
    ("inventory", "Завершена", "green"),
    ("order_products", "Не обработан", "gray"),
    ("order_products", "Принято на складе", "green"),
    ("order_products", "Перемещение", "blue"),
    ("order_products", "Заказ поставщику", "orange"),
    ("order_products", "В наличии", "green"),
    ("order_products", "Отгружено", "blue"),
    ("product_registration", "Новый", "orange"),
    ("product_registration", "В обработке", "blue"),
    ("product_registration", "Принято на складе", "green"),
]

ORDER_PRODUCT_STATUS_RENAMES = {
    "Новый": "Не обработан",
    "Не новый": "Не обработан",
    "В обработке": "Не обработан",
    "Заказ": "Заказ поставщику",
}


def _statuses_table():
    return sa.table(
        "statuses",
        sa.column("status_id", sa.BigInteger()),
        sa.column("status_type", sa.String(length=100)),
        sa.column("status_status", sa.String(length=255)),
        sa.column("status_color", sa.String(length=50)),
    )


def _order_items_table():
    return sa.table(
        "order_items",
        sa.column("order_item_status_id", sa.BigInteger()),
    )


def _orders_table():
    return sa.table(
        "orders",
        sa.column("order_status_id", sa.BigInteger()),
    )


def _get_status_id(bind, statuses_table, status_type: str, status_name: str):
    return bind.execute(
        sa.select(statuses_table.c.status_id).where(
            statuses_table.c.status_type == status_type,
            statuses_table.c.status_status == status_name,
        )
    ).scalar_one_or_none()


def _upsert_status(bind, statuses_table, status_type: str, status_name: str, status_color: str):
    status_id = _get_status_id(bind, statuses_table, status_type, status_name)
    if status_id is None:
        bind.execute(
            statuses_table.insert().values(
                status_type=status_type,
                status_status=status_name,
                status_color=status_color,
            )
        )
        return

    bind.execute(
        statuses_table.update()
        .where(statuses_table.c.status_id == status_id)
        .values(status_color=status_color)
    )


def _remap_order_item_status(bind, statuses_table, order_items_table, from_name: str, to_name: str):
    from_status_id = _get_status_id(bind, statuses_table, "order_products", from_name)
    to_status_id = _get_status_id(bind, statuses_table, "order_products", to_name)
    if from_status_id is None or to_status_id is None or from_status_id == to_status_id:
        return

    bind.execute(
        order_items_table.update()
        .where(order_items_table.c.order_item_status_id == from_status_id)
        .values(order_item_status_id=to_status_id)
    )
    bind.execute(statuses_table.delete().where(statuses_table.c.status_id == from_status_id))


def _remap_order_status(bind, statuses_table, orders_table, from_name: str, to_name: str):
    from_status_id = _get_status_id(bind, statuses_table, "orders", from_name)
    to_status_id = _get_status_id(bind, statuses_table, "orders", to_name)
    if from_status_id is None or to_status_id is None or from_status_id == to_status_id:
        return

    bind.execute(
        orders_table.update()
        .where(orders_table.c.order_status_id == from_status_id)
        .values(order_status_id=to_status_id)
    )
    bind.execute(statuses_table.delete().where(statuses_table.c.status_id == from_status_id))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("statuses"):
        return

    statuses_table = _statuses_table()
    for status_type, status_name, status_color in REQUIRED_STATUSES:
        _upsert_status(bind, statuses_table, status_type, status_name, status_color)

    if inspector.has_table("order_items"):
        order_items_table = _order_items_table()
        for from_name, to_name in ORDER_PRODUCT_STATUS_RENAMES.items():
            _remap_order_item_status(bind, statuses_table, order_items_table, from_name, to_name)
    else:
        for from_name in ORDER_PRODUCT_STATUS_RENAMES:
            from_status_id = _get_status_id(bind, statuses_table, "order_products", from_name)
            if from_status_id is not None:
                bind.execute(statuses_table.delete().where(statuses_table.c.status_id == from_status_id))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("statuses"):
        return

    statuses_table = _statuses_table()

    _upsert_status(bind, statuses_table, "order_products", "В обработке", "blue")
    _upsert_status(bind, statuses_table, "order_products", "Заказ", "orange")

    if inspector.has_table("order_items"):
        order_items_table = _order_items_table()
        _remap_order_item_status(bind, statuses_table, order_items_table, "Заказ поставщику", "Заказ")

    if inspector.has_table("orders"):
        orders_table = _orders_table()
        _remap_order_status(bind, statuses_table, orders_table, "На сборку", "В обработке")
        _remap_order_status(bind, statuses_table, orders_table, "Собран", "Выполнен")
        _remap_order_status(bind, statuses_table, orders_table, "Отменен", "Новый")

    for status_type, status_name in [
        ("orders", "На сборку"),
        ("orders", "Собран"),
        ("orders", "Отменен"),
        ("order_products", "Заказ поставщику"),
    ]:
        status_id = _get_status_id(bind, statuses_table, status_type, status_name)
        if status_id is not None:
            bind.execute(statuses_table.delete().where(statuses_table.c.status_id == status_id))