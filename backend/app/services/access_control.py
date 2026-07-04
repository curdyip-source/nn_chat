"""Права доступа к документам складов — настройки на каждый склад (per-warehouse).

У пользователя на каждом складе-членстве свой набор: view/edit/delete scope и
can_create. scope: own = только свои документы этого склада; establishment = любые
документы этого склада. Администратор обходит все проверки.
"""

from sqlalchemy.orm import Session

from app.repositories.user_establishment_roles import UserEstablishmentRoleRepository

SCOPE_NONE = "none"
SCOPE_OWN = "own"
SCOPE_ESTABLISHMENT = "establishment"

VIEW_SCOPES = (SCOPE_OWN, SCOPE_ESTABLISHMENT)
ACTION_SCOPES = (SCOPE_NONE, SCOPE_OWN, SCOPE_ESTABLISHMENT)


def _memberships(db: Session, user: dict) -> dict[int, "object"]:
    return {
        row.user_establishment_role_establishment_id: row
        for row in UserEstablishmentRoleRepository(db).list_for_user(user["user_id"])
    }


def _scope_allows(scope: str, is_owner: bool) -> bool:
    if scope == SCOPE_ESTABLISHMENT:
        return True
    if scope == SCOPE_OWN:
        return is_owner
    return False  # none


def list_visibility(db: Session, user: dict) -> tuple[set[int] | None, set[int], int]:
    """Как фильтровать список документов.

    Возвращает (full_ids, own_ids, user_id):
    - full_ids None      — без ограничения (администратор);
    - full_ids (set)     — склады, где видны ВСЕ документы (view=establishment);
    - own_ids (set)      — склады, где видны только СВОИ документы (view=own).
    Документ виден, если его склад ∈ full_ids ИЛИ (его склад ∈ own_ids и владелец=user).
    """
    if user.get("user_admin"):
        return None, set(), user["user_id"]
    full: set[int] = set()
    own: set[int] = set()
    for establishment_id, membership in _memberships(db, user).items():
        if membership.user_establishment_role_view_scope == SCOPE_ESTABLISHMENT:
            full.add(establishment_id)
        else:
            own.add(establishment_id)
    return full, own, user["user_id"]


def can_view_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    if user.get("user_admin"):
        return True
    membership = _memberships(db, user).get(establishment_id)
    if membership is None:
        return False
    return _scope_allows(membership.user_establishment_role_view_scope, owner_user_id == user["user_id"])


def can_edit_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    if user.get("user_admin"):
        return True
    membership = _memberships(db, user).get(establishment_id)
    if membership is None:
        return False
    return _scope_allows(membership.user_establishment_role_edit_scope, owner_user_id == user["user_id"])


def can_delete_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    if user.get("user_admin"):
        return True
    membership = _memberships(db, user).get(establishment_id)
    if membership is None:
        return False
    return _scope_allows(membership.user_establishment_role_delete_scope, owner_user_id == user["user_id"])


def can_create_on_establishment(db: Session, user: dict, establishment_id: int) -> bool:
    if user.get("user_admin"):
        return True
    membership = _memberships(db, user).get(establishment_id)
    return bool(membership and membership.user_establishment_role_can_create)


def can_view_message_card(db: Session, user: dict, message) -> bool:
    """Видима ли пользователю карточка-документ (заказ/инвентаризация/приёмка), встроенная
    в сообщение чата. Обычные текстовые сообщения (без документа) видимы всегда — в чате они
    общие. Для карточек — те же права по складу, что и в списках (can_view_document)."""
    if user.get("user_admin"):
        return True
    order = message.order
    if order is not None:
        return can_view_document(db, user, order.order_establishment_id, order.order_owner_user_id)
    inventory = message.inventory
    if inventory is not None:
        return can_view_document(db, user, inventory.inventory_establishment_id, inventory.inventory_owner_user_id)
    registration = message.product_registration
    if registration is not None:
        return can_view_document(
            db, user, registration.product_registration_establishment_id, registration.product_registration_owner_user_id
        )
    return True  # обычное сообщение — общее
