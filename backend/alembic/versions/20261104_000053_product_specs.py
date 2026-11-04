"""product_specs: вес и штрихкоды товара по наименованию

Revision ID: 20261104_000053
Revises: 20261102_000052
Create Date: 2026-11-04 00:00:53

Заодно один раз переносит веса из уже созданных приёмок: по каждому товару — самый
свежий. Нормализация здесь своя копия, чтобы миграция не зависела от кода приложения.
"""

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261104_000053"
down_revision = "20261102_000052"
branch_labels = None
depends_on = None


def _name_key(name: str) -> str:
    value = (name or "").strip().lower().replace("ё", "е")
    value = re.sub(r"(?<=\d)\s*(?:мл|ml)\b", "ml", value)
    return re.sub(r"\s+", " ", value)[:500]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("product_specs"):
        return
    table = op.create_table(
        "product_specs",
        sa.Column("product_spec_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("product_spec_name_key", sa.String(500), nullable=False),
        sa.Column("product_spec_name", sa.String(500), nullable=False),
        sa.Column("product_spec_weight", sa.Numeric(10, 3), nullable=True),
        sa.Column("product_spec_barcode_general", sa.String(64), nullable=True),
        sa.Column("product_spec_barcode_secondary", sa.String(64), nullable=True),
        sa.Column("product_spec_updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("product_spec_updated_by_user_id", sa.BigInteger(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_product_specs_product_spec_id", "product_specs", ["product_spec_id"])
    op.create_index("ix_product_specs_product_spec_name_key", "product_specs", ["product_spec_name_key"], unique=True)
    op.create_index("ix_product_specs_product_spec_barcode_general", "product_specs", ["product_spec_barcode_general"])
    op.create_index("ix_product_specs_product_spec_barcode_secondary", "product_specs", ["product_spec_barcode_secondary"])

    # Новые сверху: первая встреченная запись товара — самая свежая.
    rows = bind.execute(sa.text(
        "SELECT i.product_registration_item_name, i.product_registration_item_weight "
        "FROM product_registration_items i "
        "JOIN product_registrations r ON r.product_registration_id = i.product_registration_item_product_registration_id "
        "WHERE i.product_registration_item_weight IS NOT NULL "
        "ORDER BY r.product_registration_created_at DESC, i.product_registration_item_id DESC"
    )).fetchall()
    seen: dict[str, dict] = {}
    for name, weight in rows:
        key = _name_key(name)
        if key and key not in seen:
            seen[key] = {"product_spec_name_key": key, "product_spec_name": name.strip()[:500], "product_spec_weight": weight}
    if seen:
        op.bulk_insert(table, list(seen.values()))


def downgrade() -> None:
    op.drop_table("product_specs")
