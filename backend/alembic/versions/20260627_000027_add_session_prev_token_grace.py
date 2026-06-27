"""add session prev token grace columns

Revision ID: 20260627_000027
Revises: 20260626_000026
Create Date: 2026-06-27 00:00:27

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260627_000027"
down_revision = "20260626_000026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("user_sessions"):
        return

    columns = {column["name"] for column in inspector.get_columns("user_sessions")}
    indexes = {index["name"] for index in inspector.get_indexes("user_sessions")}

    if "session_prev_token" not in columns:
        op.add_column("user_sessions", sa.Column("session_prev_token", sa.String(length=255), nullable=True))
    if "session_prev_token_expires_at" not in columns:
        op.add_column("user_sessions", sa.Column("session_prev_token_expires_at", sa.DateTime(), nullable=True))
    if "ix_user_sessions_session_prev_token" not in indexes:
        op.create_index("ix_user_sessions_session_prev_token", "user_sessions", ["session_prev_token"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("user_sessions"):
        return

    columns = {column["name"] for column in inspector.get_columns("user_sessions")}
    indexes = {index["name"] for index in inspector.get_indexes("user_sessions")}

    if "ix_user_sessions_session_prev_token" in indexes:
        op.drop_index("ix_user_sessions_session_prev_token", table_name="user_sessions")
    if "session_prev_token_expires_at" in columns:
        op.drop_column("user_sessions", "session_prev_token_expires_at")
    if "session_prev_token" in columns:
        op.drop_column("user_sessions", "session_prev_token")
