"""add user device apns environment

Revision ID: 20260623_000025
Revises: 20260617_000024
Create Date: 2026-06-23 00:00:25

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260623_000025"
down_revision = "20260617_000024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("user_devices"):
        return

    columns = {column["name"] for column in inspector.get_columns("user_devices")}
    if "user_device_environment" not in columns:
        # Existing tokens were registered against the production APNs gateway,
        # so backfill them as "production" to keep current pushes working.
        op.add_column(
            "user_devices",
            sa.Column("user_device_environment", sa.String(length=20), nullable=False, server_default="production"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("user_devices"):
        return

    columns = {column["name"] for column in inspector.get_columns("user_devices")}
    if "user_device_environment" in columns:
        op.drop_column("user_devices", "user_device_environment")
