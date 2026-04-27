"""add profile photos

Revision ID: 20260330_000011
Revises: 20260325_000010
Create Date: 2026-03-30 00:00:11

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260330_000011"
down_revision = "20260325_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("profile_photos"):
        op.create_table(
            "profile_photos",
            sa.Column("profile_photo_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False),
            sa.Column("profile_photo_mime_type", sa.String(length=100), nullable=False),
            sa.Column("profile_photo_bytes", sa.LargeBinary(), nullable=False),
            sa.Column("profile_photo_updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_profile_photos_profile_photo_user_id", "profile_photos", ["profile_photo_user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("profile_photos"):
        op.drop_index("ix_profile_photos_profile_photo_user_id", table_name="profile_photos")
        op.drop_table("profile_photos")