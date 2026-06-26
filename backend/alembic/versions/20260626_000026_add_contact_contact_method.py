"""add contact contact method

Revision ID: 20260626_000026
Revises: 20260623_000025
Create Date: 2026-06-26 00:00:26

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260626_000026"
down_revision = "20260623_000025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("contacts"):
        return

    columns = {column["name"] for column in inspector.get_columns("contacts")}
    if "contact_contact_method" not in columns:
        op.add_column("contacts", sa.Column("contact_contact_method", sa.String(length=50), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("contacts"):
        return

    columns = {column["name"] for column in inspector.get_columns("contacts")}
    if "contact_contact_method" in columns:
        op.drop_column("contacts", "contact_contact_method")
