"""todo lists and tasks (тудулист)

Revision ID: 20260807_000042
Revises: 20260807_000041
Create Date: 2026-08-07 00:00:42

Личный менеджер задач: пользовательские списки, задачи («когда сделать» и дедлайн —
дата со временем, метки, архив) и подзадачи чек-листом. Умные списки (Входящие, Сегодня,
Запланировано, Когда-нибудь, Архив) в базе не хранятся — считаются по полям задачи.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260807_000042"
down_revision = "20260807_000041"
branch_labels = None
depends_on = None

ID_TYPE = sa.BigInteger().with_variant(sa.Integer, "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "todo_lists" not in tables:
        op.create_table(
            "todo_lists",
            sa.Column("todo_list_id", ID_TYPE, primary_key=True),
            sa.Column("todo_list_owner_user_id", ID_TYPE, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("todo_list_name", sa.String(length=100), nullable=False),
            sa.Column("todo_list_position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("todo_list_created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_todo_lists_todo_list_id", "todo_lists", ["todo_list_id"])
        op.create_index("ix_todo_lists_todo_list_owner_user_id", "todo_lists", ["todo_list_owner_user_id"])

    if "todos" not in tables:
        op.create_table(
            "todos",
            sa.Column("todo_id", ID_TYPE, primary_key=True),
            sa.Column("todo_owner_user_id", ID_TYPE, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("todo_list_id", ID_TYPE, sa.ForeignKey("todo_lists.todo_list_id", ondelete="SET NULL"), nullable=True),
            sa.Column("todo_title", sa.String(length=500), nullable=False),
            sa.Column("todo_note", sa.Text(), nullable=True),
            sa.Column("todo_do_at", sa.DateTime(), nullable=True),
            sa.Column("todo_deadline_at", sa.DateTime(), nullable=True),
            sa.Column("todo_someday", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("todo_tags", sa.JSON(), nullable=True),
            sa.Column("todo_completed_at", sa.DateTime(), nullable=True),
            sa.Column("todo_archived", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("todo_position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("todo_created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_todos_todo_id", "todos", ["todo_id"])
        op.create_index("ix_todos_todo_owner_user_id", "todos", ["todo_owner_user_id"])
        op.create_index("ix_todos_todo_list_id", "todos", ["todo_list_id"])
        op.create_index("ix_todos_todo_do_at", "todos", ["todo_do_at"])
        op.create_index("ix_todos_todo_archived", "todos", ["todo_archived"])

    if "todo_subtasks" not in tables:
        op.create_table(
            "todo_subtasks",
            sa.Column("todo_subtask_id", ID_TYPE, primary_key=True),
            sa.Column("todo_subtask_todo_id", ID_TYPE, sa.ForeignKey("todos.todo_id", ondelete="CASCADE"), nullable=False),
            sa.Column("todo_subtask_title", sa.String(length=500), nullable=False),
            sa.Column("todo_subtask_done", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("todo_subtask_position", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_todo_subtasks_todo_subtask_id", "todo_subtasks", ["todo_subtask_id"])
        op.create_index("ix_todo_subtasks_todo_subtask_todo_id", "todo_subtasks", ["todo_subtask_todo_id"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "todo_subtasks" in tables:
        op.drop_table("todo_subtasks")
    if "todos" in tables:
        op.drop_table("todos")
    if "todo_lists" in tables:
        op.drop_table("todo_lists")
