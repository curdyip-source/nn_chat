from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.reference_data import ProductRepository, ReferenceDataRepository
from app.services.reference_data import ensure_reference_data


def get_establishment_or_404(db: Session, establishment_id: int):
    row = ReferenceDataRepository(db).get_establishment(establishment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Точка не найдена")
    return row


def get_order_method_or_404(db: Session, order_method_id: int):
    row = ReferenceDataRepository(db).get_order_method(order_method_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Способ заказа не найден")
    return row


def get_status_or_404(db: Session, status_id: int, *, expected_type: str | None = None):
    row = ReferenceDataRepository(db).get_status(status_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Статус не найден")
    if expected_type is not None and row.status_type != expected_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан статус другого типа")
    return row


def get_default_status_or_400(db: Session, *, status_type: str):
    ensure_reference_data(db)
    default_name = "Не обработан" if status_type == "order_products" else "Новый"
    row = ReferenceDataRepository(db).get_status_by_type_and_name(status_type, default_name)
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Не найден базовый статус '{default_name}'")
    return row


def get_default_currency_or_400(db: Session):
    ensure_reference_data(db)
    row = ReferenceDataRepository(db).get_currency_by_name("USD")
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не найдена валюта USD")
    return row


def resolve_product_snapshot(db: Session, *, current_user: dict, product_id: int | None, product_article: str | None, product_name: str | None, product_cost_usd):
    repository = ProductRepository(db)
    if product_id is not None:
        row = repository.get_by_id(product_id)
        if row is not None:
            return row, row.product_article, row.product_name, product_cost_usd
        # Товар мог быть удалён/пересобран при федерации каталога (nn_vla). НЕ падаем
        # 404: если пришёл снимок (артикул+название) — восстанавливаем позицию по нему
        # (find-by-article или создание); иначе позиция сохранит снимок без ссылки на
        # каталог. Заказ не должен ломаться из-за churn'а каталога.
    if product_article is None or product_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для нового товара нужны артикул и название")
    existing = repository.get_by_article(product_article)
    if existing is not None:
        return existing, existing.product_article, existing.product_name, product_cost_usd
    created = repository.create(
        {
            "product_article": product_article,
            "product_name": product_name,
            "product_cost_usd": product_cost_usd,
            "product_owner_user_id": current_user["user_id"],
        }
    )
    return created, created.product_article, created.product_name, product_cost_usd