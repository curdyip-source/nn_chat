"""user allowed order statuses (ось C)

Revision ID: 20260712_000036
Revises: 20260704_000035
Create Date: 2026-07-12 00:00:36

Разрешённые статусы заказа на пользователя. NULL/пусто = без ограничения (обратная
совместимость). Список status_id = пользователь видит и может назначать только заказы в
этих статусах (напр. отгрузочный — только «На сборку» и «Собран»).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260712_000036"
down_revision = "20260704_000035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("users"):
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "user_order_statuses" not in cols:
            op.add_column("users", sa.Column("user_order_statuses", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("users"):
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "user_order_statuses" in cols:
            op.drop_column("users", "user_order_statuses")
