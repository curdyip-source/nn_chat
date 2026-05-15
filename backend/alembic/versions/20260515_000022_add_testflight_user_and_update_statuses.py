"""add testflight user and update statuses

Revision ID: 20260515_000022
Revises: 20260510_000021
Create Date: 2026-05-15 00:00:22

"""

import base64
import hashlib
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260515_000022"
down_revision = "20260510_000021"
branch_labels = None
depends_on = None


TEST_USER_LOGIN = "test_user"
TEST_USER_PASSWORD = "VVupv2J=Ya"
ORDER_STATUS_COLORS = {
    "Собран": "#0f766e",
    "Выполнен": "#16a34a",
}
ORDER_PRODUCT_STATUSES = {
    "Не будет": "red",
}


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return "pbkdf2_sha256${}${}${}".format(
        120000,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(hashed).decode("utf-8"),
    )


def _users_table():
    return sa.table(
        "users",
        sa.column("user_id", sa.BigInteger()),
        sa.column("user_login", sa.String(length=100)),
        sa.column("user_password", sa.Text()),
        sa.column("user_admin", sa.Boolean()),
        sa.column("user_active", sa.Boolean()),
        sa.column("user_first_name", sa.String(length=100)),
        sa.column("user_second_name", sa.String(length=100)),
        sa.column("user_age", sa.Integer()),
        sa.column("user_address", sa.Text()),
    )


def _statuses_table():
    return sa.table(
        "statuses",
        sa.column("status_id", sa.BigInteger()),
        sa.column("status_type", sa.String(length=100)),
        sa.column("status_status", sa.String(length=255)),
        sa.column("status_color", sa.String(length=50)),
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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("users"):
        users_table = _users_table()
        existing_user_id = bind.execute(
            sa.select(users_table.c.user_id).where(users_table.c.user_login == TEST_USER_LOGIN)
        ).scalar_one_or_none()
        user_values = {
            "user_password": _hash_password(TEST_USER_PASSWORD),
            "user_admin": False,
            "user_active": True,
        }
        if existing_user_id is None:
            bind.execute(
                users_table.insert().values(
                    user_login=TEST_USER_LOGIN,
                    user_first_name="Test",
                    user_second_name="User",
                    user_age=0,
                    user_address="TestFlight public tests",
                    **user_values,
                )
            )
        else:
            bind.execute(
                users_table.update()
                .where(users_table.c.user_id == existing_user_id)
                .values(**user_values)
            )

    if not inspector.has_table("statuses"):
        return

    statuses_table = _statuses_table()
    for status_name, status_color in ORDER_STATUS_COLORS.items():
        _upsert_status(bind, statuses_table, "orders", status_name, status_color)
    for status_name, status_color in ORDER_PRODUCT_STATUSES.items():
        _upsert_status(bind, statuses_table, "order_products", status_name, status_color)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("statuses"):
        return

    statuses_table = _statuses_table()
    _upsert_status(bind, statuses_table, "orders", "Собран", "#16a34a")
    _upsert_status(bind, statuses_table, "orders", "Выполнен", "#0f766e")

    not_will_status_id = _get_status_id(bind, statuses_table, "order_products", "Не будет")
    if not_will_status_id is not None:
        bind.execute(statuses_table.delete().where(statuses_table.c.status_id == not_will_status_id))