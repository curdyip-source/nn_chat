"""Справочник характеристик товара по наименованию: вес подставляется в приёмку."""

import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.product_specs import ProductSpec

_UNIT_RE = re.compile(r"(?<=\d)\s*(?:мл|ml)\b")
_SPACES_RE = re.compile(r"\s+")


def normalize_product_name(name: str | None) -> str:
    """Ключ: регистр, ё→е, «100 мл»→«100ml», лишние пробелы. Как search_text прайса."""
    value = (name or "").strip().lower().replace("ё", "е")
    value = _UNIT_RE.sub("ml", value)
    return _SPACES_RE.sub(" ", value)[:500]


def weights_for_names(db: Session, names: list[str]) -> dict[str, Decimal]:
    """{ключ наименования: вес} — одним запросом на всю пачку товаров."""
    keys = {normalize_product_name(name) for name in names}
    keys.discard("")
    if not keys:
        return {}
    rows = (
        db.query(ProductSpec.product_spec_name_key, ProductSpec.product_spec_weight)
        .filter(ProductSpec.product_spec_name_key.in_(keys), ProductSpec.product_spec_weight.isnot(None))
        .all()
    )
    return {key: weight for key, weight in rows}


def attach_weights(db: Session, products: list[dict]) -> list[dict]:
    """Добавить product_weight в сериализованные товары (нет веса — null)."""
    weights = weights_for_names(db, [product["product_name"] for product in products])
    for product in products:
        weight = weights.get(normalize_product_name(product["product_name"]))
        product["product_weight"] = format(weight, "f") if weight is not None else None
    return products


def set_product_weight(db: Session, name: str, weight: Decimal | None, user_id: int | None) -> None:
    """Перезаписать вес товара (None — стереть). Коммит — на вызывающей стороне."""
    key = normalize_product_name(name)
    if not key:
        return
    row = db.query(ProductSpec).filter(ProductSpec.product_spec_name_key == key).first()
    if row is None:
        if weight is None:
            return
        row = ProductSpec(product_spec_name_key=key, product_spec_name=name.strip()[:500])
        db.add(row)
    row.product_spec_weight = weight
    row.product_spec_updated_at = datetime.utcnow()
    row.product_spec_updated_by_user_id = user_id
    db.flush()
