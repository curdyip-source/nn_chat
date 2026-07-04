"""user permission profile: scope fields on users + membership-only roles

Revision ID: 20260704_000033
Revises: 20260704_000032
Create Date: 2026-07-04 00:00:33

Профиль прав переносится на пользователя (view/create/edit/delete scope), а таблица
user_establishment_roles становится чистым членством в складах (колонка role убрана).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260704_000033"
down_revision = "20260704_000032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    user_columns = {c["name"] for c in inspector.get_columns("users")} if inspector.has_table("users") else set()
    if "user_view_scope" not in user_columns:
        op.add_column("users", sa.Column("user_view_scope", sa.String(length=20), nullable=False, server_default="establishment"))
    if "user_can_create" not in user_columns:
        op.add_column("users", sa.Column("user_can_create", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "user_edit_scope" not in user_columns:
        op.add_column("users", sa.Column("user_edit_scope", sa.String(length=20), nullable=False, server_default="none"))
    if "user_delete_scope" not in user_columns:
        op.add_column("users", sa.Column("user_delete_scope", sa.String(length=20), nullable=False, server_default="none"))

    if inspector.has_table("user_establishment_roles"):
        role_columns = {c["name"] for c in inspector.get_columns("user_establishment_roles")}
        if "user_establishment_role_role" in role_columns:
            op.drop_column("user_establishment_roles", "user_establishment_role_role")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("user_establishment_roles"):
        role_columns = {c["name"] for c in inspector.get_columns("user_establishment_roles")}
        if "user_establishment_role_role" not in role_columns:
            op.add_column("user_establishment_roles", sa.Column("user_establishment_role_role", sa.String(length=20), nullable=False, server_default="viewer"))

    user_columns = {c["name"] for c in inspector.get_columns("users")} if inspector.has_table("users") else set()
    for column in ("user_delete_scope", "user_edit_scope", "user_can_create", "user_view_scope"):
        if column in user_columns:
            op.drop_column("users", column)
