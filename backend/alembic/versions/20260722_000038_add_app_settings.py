"""add app_settings (key-value; min_supported_ios_build для гейта форс-апдейта)

Revision ID: 20260722_000038
Revises: 20260722_000037
Create Date: 2026-07-22 00:00:38
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260722_000038"
down_revision = "20260722_000037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("app_settings"):
        return
    op.create_table(
        "app_settings",
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=True),
        sa.Column("setting_updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("setting_key"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("app_settings"):
        op.drop_table("app_settings")
