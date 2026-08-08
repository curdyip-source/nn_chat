"""todo: привязка к заказу и ответственные

Revision ID: 20260808_000043
Revises: 20260807_000042
Create Date: 2026-08-08 00:00:43

Задача может быть привязана к заказу — такая задача общая: её видит любой, кому
виден сам заказ (склад + статусы), она показывается в карточке заказа и считается
в бабле в списках СРМ. При удалении заказа задача остаётся и просто теряет привязку.

Ответственные — отдельная таблица «многие ко многим»: задача попадает в тудулист
назначенного и он получает пуш.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260808_000043"
down_revision = "20260807_000042"
branch_labels = None
depends_on = None

ID_TYPE = sa.BigInteger().with_variant(sa.Integer, "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "todos" in tables:
        columns = {column["name"] for column in inspector.get_columns("todos")}
        if "todo_order_id" not in columns:
            op.add_column(
                "todos",
                sa.Column(
                    "todo_order_id",
                    ID_TYPE,
                    sa.ForeignKey("orders.order_id", ondelete="SET NULL", name="fk_todos_order"),
                    nullable=True,
                ),
            )
            op.create_index("ix_todos_todo_order_id", "todos", ["todo_order_id"])

    if "todo_assignees" not in tables:
        op.create_table(
            "todo_assignees",
            sa.Column("todo_assignee_id", ID_TYPE, primary_key=True),
            sa.Column("todo_assignee_todo_id", ID_TYPE, sa.ForeignKey("todos.todo_id", ondelete="CASCADE"), nullable=False),
            sa.Column("todo_assignee_user_id", ID_TYPE, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("todo_assignee_created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("todo_assignee_todo_id", "todo_assignee_user_id", name="uq_todo_assignee"),
        )
        op.create_index("ix_todo_assignees_todo_assignee_id", "todo_assignees", ["todo_assignee_id"])
        op.create_index("ix_todo_assignees_todo_assignee_todo_id", "todo_assignees", ["todo_assignee_todo_id"])
        op.create_index("ix_todo_assignees_todo_assignee_user_id", "todo_assignees", ["todo_assignee_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "todo_assignees" in tables:
        op.drop_table("todo_assignees")
    if "todos" in tables:
        columns = {column["name"] for column in inspector.get_columns("todos")}
        if "todo_order_id" in columns:
            op.drop_column("todos", "todo_order_id")
