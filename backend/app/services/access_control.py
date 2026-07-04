"""Права доступа к документам складов (ось C) — профиль на пользователе + членство.

Модель (Вариант 1):
- Членство в складах (user_establishment_roles) — множество складов «мои».
- Профиль прав на пользователе: view/edit/delete scope и can_create.
  scope: own = только свои документы; establishment = в моих складах; all = во всех.
Администратор обходит все проверки.
"""

from sqlalchemy.orm import Session

from app.repositories.user_establishment_roles import UserEstablishmentRoleRepository

SCOPE_NONE = "none"
SCOPE_OWN = "own"
SCOPE_ESTABLISHMENT = "establishment"
SCOPE_ALL = "all"

VIEW_SCOPES = (SCOPE_OWN, SCOPE_ESTABLISHMENT, SCOPE_ALL)
ACTION_SCOPES = (SCOPE_NONE, SCOPE_OWN, SCOPE_ESTABLISHMENT, SCOPE_ALL)


def member_establishment_ids(db: Session, user: dict) -> set[int]:
    """Склады, в которых пользователь состоит (его «мои склады»)."""
    return {
        row.user_establishment_role_establishment_id
        for row in UserEstablishmentRoleRepository(db).list_for_user(user["user_id"])
    }


def _scope_allows(db: Session, user: dict, scope: str, establishment_id: int, owner_user_id: int) -> bool:
    if scope == SCOPE_ALL:
        return True
    if scope == SCOPE_ESTABLISHMENT:
        return establishment_id in member_establishment_ids(db, user)
    if scope == SCOPE_OWN:
        return owner_user_id == user["user_id"]
    return False  # none


def list_visibility(db: Session, user: dict) -> tuple[set[int] | None, int | None]:
    """Как фильтровать список документов под область видимости пользователя.

    Возвращает (establishment_ids, owner_user_id):
    - (None, None)  — без ограничения (админ или view=all);
    - (set, None)   — только документы этих складов (view=establishment);
    - (None, uid)   — только свои документы (view=own).
    """
    if user.get("user_admin") or user.get("user_view_scope") == SCOPE_ALL:
        return None, None
    if user.get("user_view_scope") == SCOPE_OWN:
        return None, user["user_id"]
    return member_establishment_ids(db, user), None  # establishment


def can_view_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    if user.get("user_admin"):
        return True
    return _scope_allows(db, user, user.get("user_view_scope", SCOPE_OWN), establishment_id, owner_user_id)


def can_edit_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    if user.get("user_admin"):
        return True
    return _scope_allows(db, user, user.get("user_edit_scope", SCOPE_NONE), establishment_id, owner_user_id)


def can_delete_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    if user.get("user_admin"):
        return True
    return _scope_allows(db, user, user.get("user_delete_scope", SCOPE_NONE), establishment_id, owner_user_id)


def can_create_on_establishment(db: Session, user: dict, establishment_id: int) -> bool:
    if user.get("user_admin"):
        return True
    if not user.get("user_can_create"):
        return False
    # Создавать можно в складах-членствах (или в любом, если область создания = все склады).
    if user.get("user_view_scope") == SCOPE_ALL or user.get("user_edit_scope") == SCOPE_ALL:
        return True
    return establishment_id in member_establishment_ids(db, user)
