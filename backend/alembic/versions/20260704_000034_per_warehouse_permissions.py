"""per-warehouse permission settings: move scope fields onto membership

Revision ID: 20260704_000034
Revises: 20260704_000033
Create Date: 2026-07-04 00:00:34

Настройки прав переносятся с пользователя на каждую строку членства (свои настройки
на каждом складе): user_establishment_roles получает view/can_create/edit/delete,
а глобальные поля профиля с users убираются.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260704_000034"
down_revision = "20260704_000033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("user_establishment_roles"):
        cols = {c["name"] for c in inspector.get_columns("user_establishment_roles")}
        if "user_establishment_role_view_scope" not in cols:
            op.add_column("user_establishment_roles", sa.Column("user_establishment_role_view_scope", sa.String(length=20), nullable=False, server_default="establishment"))
        if "user_establishment_role_can_create" not in cols:
            op.add_column("user_establishment_roles", sa.Column("user_establishment_role_can_create", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "user_establishment_role_edit_scope" not in cols:
            op.add_column("user_establishment_roles", sa.Column("user_establishment_role_edit_scope", sa.String(length=20), nullable=False, server_default="none"))
        if "user_establishment_role_delete_scope" not in cols:
            op.add_column("user_establishment_roles", sa.Column("user_establishment_role_delete_scope", sa.String(length=20), nullable=False, server_default="none"))

    user_cols = {c["name"] for c in inspector.get_columns("users")} if inspector.has_table("users") else set()
    for column in ("user_view_scope", "user_can_create", "user_edit_scope", "user_delete_scope"):
        if column in user_cols:
            op.drop_column("users", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    user_cols = {c["name"] for c in inspector.get_columns("users")} if inspector.has_table("users") else set()
    if "user_view_scope" not in user_cols:
        op.add_column("users", sa.Column("user_view_scope", sa.String(length=20), nullable=False, server_default="establishment"))
    if "user_can_create" not in user_cols:
        op.add_column("users", sa.Column("user_can_create", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "user_edit_scope" not in user_cols:
        op.add_column("users", sa.Column("user_edit_scope", sa.String(length=20), nullable=False, server_default="none"))
    if "user_delete_scope" not in user_cols:
        op.add_column("users", sa.Column("user_delete_scope", sa.String(length=20), nullable=False, server_default="none"))

    if inspector.has_table("user_establishment_roles"):
        cols = {c["name"] for c in inspector.get_columns("user_establishment_roles")}
        for column in ("user_establishment_role_delete_scope", "user_establishment_role_edit_scope", "user_establishment_role_can_create", "user_establishment_role_view_scope"):
            if column in cols:
                op.drop_column("user_establishment_roles", column)
