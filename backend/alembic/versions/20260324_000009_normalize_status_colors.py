"""normalize status colors

Revision ID: 20260324_000009
Revises: 20260324_000008
Create Date: 2026-03-24 00:00:09

"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_000009"
down_revision = "20260324_000008"
branch_labels = None
depends_on = None


STATUS_COLORS = [
    ("orders", "Новый", "orange"),
    ("orders", "В обработке", "blue"),
    ("orders", "Выполнен", "green"),
    ("inventory", "Новый", "orange"),
    ("inventory", "В обработке", "blue"),
    ("inventory", "Завершена", "green"),
    ("order_products", "Новый", "orange"),
    ("order_products", "В обработке", "blue"),
    ("order_products", "Принято на складе", "green"),
    ("product_registration", "Новый", "orange"),
    ("product_registration", "В обработке", "blue"),
    ("product_registration", "Принято на складе", "green"),
]


def upgrade() -> None:
    bind = op.get_bind()
    statement = sa.text(
        """
        UPDATE statuses
        SET status_color = :status_color
        WHERE status_type = :status_type AND status_status = :status_status
        """
    )
    for status_type, status_status, status_color in STATUS_COLORS:
        bind.execute(
            statement,
            {
                "status_type": status_type,
                "status_status": status_status,
                "status_color": status_color,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    statement = sa.text(
        """
        UPDATE statuses
        SET status_color = :status_color
        WHERE status_type = :status_type AND status_status = :status_status
        """
    )
    rollback_colors = {
        ("orders", "Выполнен"): None,
    }
    for status_type, status_status, _ in STATUS_COLORS:
        bind.execute(
            statement,
            {
                "status_type": status_type,
                "status_status": status_status,
                "status_color": rollback_colors.get((status_type, status_status), "1"),
            },
        )