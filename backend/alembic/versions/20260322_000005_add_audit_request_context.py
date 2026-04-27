"""add audit request context

Revision ID: 20260322_000005
Revises: 20260322_000004
Create Date: 2026-03-22 00:00:05

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260322_000005"
down_revision = "20260322_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("audit_events"):
        return

    columns = {column["name"] for column in inspector.get_columns("audit_events")}
    if "request_id" not in columns:
        op.add_column("audit_events", sa.Column("request_id", sa.String(length=64), nullable=True))
    if "ip_address" not in columns:
        op.add_column("audit_events", sa.Column("ip_address", sa.String(length=64), nullable=True))
    if "user_agent" not in columns:
        op.add_column("audit_events", sa.Column("user_agent", sa.Text(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_request_id" not in indexes:
        op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("audit_events"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_request_id" in indexes:
        op.drop_index("ix_audit_events_request_id", table_name="audit_events")

    columns = {column["name"] for column in inspector.get_columns("audit_events")}
    if "user_agent" in columns:
        op.drop_column("audit_events", "user_agent")
    if "ip_address" in columns:
        op.drop_column("audit_events", "ip_address")
    if "request_id" in columns:
        op.drop_column("audit_events", "request_id")