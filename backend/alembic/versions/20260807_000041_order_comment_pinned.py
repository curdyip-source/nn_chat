"""pinned order chat messages (закреплённые сообщения чата заказа)

Revision ID: 20260807_000041
Revises: 20260806_000040
Create Date: 2026-08-07 00:00:41

Закрепление сообщения в чате заказа: текст закреплённых сообщений выводится в
карточке заказа в списках СРМ («Все заказы», «Отгрузки»). Максимум 3 на заказ —
лимит проверяется в сервисе, в схеме это обычный булев флаг.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260807_000041"
down_revision = "20260806_000040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_comments"):
        return
    columns = {column["name"] for column in inspector.get_columns("order_comments")}

    if "order_comment_is_pinned" not in columns:
        op.add_column(
            "order_comments",
            sa.Column("order_comment_is_pinned", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("order_comments"):
        return
    columns = {column["name"] for column in inspector.get_columns("order_comments")}

    if "order_comment_is_pinned" in columns:
        op.drop_column("order_comments", "order_comment_is_pinned")
