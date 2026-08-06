"""order method becomes optional (способ заказа может быть не выбран)

Revision ID: 20260806_000040
Revises: 20260806_000039
Create Date: 2026-08-06 00:00:40

Заказы с сайта приходят без способа заказа — его выбирает менеджер. Раньше поле
было обязательным, и приходилось ставить заглушку «Курьер», которая вводила в
заблуждение.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260806_000040"
down_revision = "20260806_000039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("orders"):
        return
    op.alter_column("orders", "order_method_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("orders"):
        return
    # Обратно в NOT NULL можно только если пустых значений не осталось.
    op.alter_column("orders", "order_method_id", existing_type=sa.BigInteger(), nullable=False)
