"""split price access: web_price (раздел веба) отдельно от режима price (поиск в приложении)

Revision ID: 20261023_000049
Revises: 20260923_000048
Create Date: 2026-10-23 00:00:49

Ключ "price" одновременно открывал поиск по прайсу в приложении и целый раздел
«Прайс» в вебе (сопоставления, выгрузки, контрагенты). Теперь веб-раздел — свой
ключ "web_price" в «Разделах СРМ (веб)», а "price" остаётся режимом приложения.
Чтобы ни у кого не пропал текущий доступ, всем, у кого есть "price", добавляем
"web_price".
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261023_000049"
down_revision = "20260923_000048"
branch_labels = None
depends_on = None


def _rewrite_sections(transform) -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("users"):
        return
    rows = bind.execute(sa.text("SELECT user_id, user_sections FROM users WHERE user_sections IS NOT NULL")).fetchall()
    for user_id, raw in rows:
        sections = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(sections, list):
            continue
        updated = transform(sections)
        if updated != sections:
            bind.execute(
                sa.text("UPDATE users SET user_sections = :sections WHERE user_id = :user_id").bindparams(
                    sa.bindparam("sections", type_=sa.JSON)
                ),
                {"sections": updated, "user_id": user_id},
            )


def upgrade() -> None:
    _rewrite_sections(lambda s: s + ["web_price"] if "price" in s and "web_price" not in s else s)


def downgrade() -> None:
    _rewrite_sections(lambda s: [key for key in s if key != "web_price"])
