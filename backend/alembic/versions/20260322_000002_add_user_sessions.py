"""add user sessions

Revision ID: 20260322_000002
Revises: 20260322_000001
Create Date: 2026-03-22 00:00:02

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260322_000002"
down_revision = "20260322_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("session_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("session_token", sa.String(length=255), nullable=False),
            sa.Column("session_user_id", sa.BigInteger(), nullable=False),
            sa.Column("session_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("session_expires_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.UniqueConstraint("session_token", name="uq_user_sessions_session_token"),
        )

    session_indexes = {index["name"] for index in inspector.get_indexes("user_sessions")}
    if "ix_user_sessions_session_id" not in session_indexes:
        op.create_index("ix_user_sessions_session_id", "user_sessions", ["session_id"], unique=False)
    if "ix_user_sessions_session_token" not in session_indexes:
        op.create_index("ix_user_sessions_session_token", "user_sessions", ["session_token"], unique=False)
    if "ix_user_sessions_session_user_id" not in session_indexes:
        op.create_index("ix_user_sessions_session_user_id", "user_sessions", ["session_user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("user_sessions"):
        session_indexes = {index["name"] for index in inspector.get_indexes("user_sessions")}
        if "ix_user_sessions_session_user_id" in session_indexes:
            op.drop_index("ix_user_sessions_session_user_id", table_name="user_sessions")
        if "ix_user_sessions_session_token" in session_indexes:
            op.drop_index("ix_user_sessions_session_token", table_name="user_sessions")
        if "ix_user_sessions_session_id" in session_indexes:
            op.drop_index("ix_user_sessions_session_id", table_name="user_sessions")
        op.drop_table("user_sessions")