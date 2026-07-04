"""user allowed menu sections (ось A)

Revision ID: 20260704_000035
Revises: 20260704_000034
Create Date: 2026-07-04 00:00:35

Разрешённые разделы меню на пользователя. NULL = все операционные разделы (обратная
совместимость). Список = только эти разделы.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260704_000035"
down_revision = "20260704_000034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("users"):
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "user_sections" not in cols:
            op.add_column("users", sa.Column("user_sections", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("users"):
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "user_sections" in cols:
            op.drop_column("users", "user_sections")
