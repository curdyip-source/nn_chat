"""Область видимости пользователя по складам (ось B прав).

Роль на складе (user_establishment_roles) = доступ к его данным. Администратор
видит все склады. Обычный пользователь — только те, где ему назначена роль.
"""

from sqlalchemy.orm import Session

from app.repositories.user_establishment_roles import UserEstablishmentRoleRepository


def accessible_establishment_ids(db: Session, user: dict) -> set[int] | None:
    """Множество id складов, доступных пользователю.

    None  — доступны все склады (администратор), фильтровать не нужно.
    set() — нет доступа ни к одному складу (пустая выдача).
    """
    if user.get("user_admin"):
        return None
    rows = UserEstablishmentRoleRepository(db).list_for_user(user["user_id"])
    return {row.user_establishment_role_establishment_id for row in rows}


def can_access_establishment(db: Session, user: dict, establishment_id: int) -> bool:
    accessible = accessible_establishment_ids(db, user)
    return accessible is None or establishment_id in accessible


def role_on_establishment(db: Session, user: dict, establishment_id: int) -> str | None:
    """Роль пользователя на складе (viewer/editor/manager) или None. Админ → 'admin'."""
    if user.get("user_admin"):
        return "admin"
    for row in UserEstablishmentRoleRepository(db).list_for_user(user["user_id"]):
        if row.user_establishment_role_establishment_id == establishment_id:
            return row.user_establishment_role_role
    return None


def can_edit_establishment_document(db: Session, user: dict, establishment_id: int, owner_user_id: int) -> bool:
    """Ось C: редактировать документ склада может админ; владелец (свой — даже viewer);
    либо роль editor/manager на этом складе. viewer чужой документ править не может."""
    if user.get("user_admin"):
        return True
    if owner_user_id == user["user_id"]:
        return True
    return role_on_establishment(db, user, establishment_id) in ("editor", "manager")
