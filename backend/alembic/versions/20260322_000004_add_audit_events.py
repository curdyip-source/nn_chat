"""add audit events

Revision ID: 20260322_000004
Revises: 20260322_000003
Create Date: 2026-03-22 00:00:04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260322_000004"
down_revision = "20260322_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("audit_event_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
            sa.Column("entity_type", sa.String(length=100), nullable=False),
            sa.Column("entity_id", sa.BigInteger(), nullable=True),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("event_payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.user_id"], ondelete="SET NULL"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_audit_event_id" not in indexes:
        op.create_index("ix_audit_events_audit_event_id", "audit_events", ["audit_event_id"], unique=False)
    if "ix_audit_events_actor_user_id" not in indexes:
        op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"], unique=False)
    if "ix_audit_events_entity_type" not in indexes:
        op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"], unique=False)
    if "ix_audit_events_entity_id" not in indexes:
        op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"], unique=False)
    if "ix_audit_events_event_type" not in indexes:
        op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"], unique=False)
    if "ix_audit_events_created_at" not in indexes:
        op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("audit_events"):
        indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
        if "ix_audit_events_created_at" in indexes:
            op.drop_index("ix_audit_events_created_at", table_name="audit_events")
        if "ix_audit_events_event_type" in indexes:
            op.drop_index("ix_audit_events_event_type", table_name="audit_events")
        if "ix_audit_events_entity_id" in indexes:
            op.drop_index("ix_audit_events_entity_id", table_name="audit_events")
        if "ix_audit_events_entity_type" in indexes:
            op.drop_index("ix_audit_events_entity_type", table_name="audit_events")
        if "ix_audit_events_actor_user_id" in indexes:
            op.drop_index("ix_audit_events_actor_user_id", table_name="audit_events")
        if "ix_audit_events_audit_event_id" in indexes:
            op.drop_index("ix_audit_events_audit_event_id", table_name="audit_events")
        op.drop_table("audit_events")