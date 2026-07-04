from sqlalchemy.orm import Session

from app.models.user_establishment_roles import UserEstablishmentRole


class UserEstablishmentRoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: int) -> list[UserEstablishmentRole]:
        return (
            self.db.query(UserEstablishmentRole)
            .filter(UserEstablishmentRole.user_establishment_role_user_id == user_id)
            .order_by(UserEstablishmentRole.user_establishment_role_establishment_id)
            .all()
        )

    def replace_for_user(self, user_id: int, settings: list[dict]) -> list[UserEstablishmentRole]:
        # Полная замена настроек прав пользователя по складам. settings — список dict со
        # ключами establishment_id, view_scope, can_create, edit_scope, delete_scope.
        # Удаляем через ORM-объекты (не bulk), чтобы identity map оставалась консистентной.
        for existing in self.list_for_user(user_id):
            self.db.delete(existing)
        self.db.flush()
        seen: set[int] = set()
        for entry in settings:
            establishment_id = entry["establishment_id"]
            if establishment_id in seen:
                continue
            seen.add(establishment_id)
            self.db.add(
                UserEstablishmentRole(
                    user_establishment_role_user_id=user_id,
                    user_establishment_role_establishment_id=establishment_id,
                    user_establishment_role_view_scope=entry["view_scope"],
                    user_establishment_role_can_create=entry["can_create"],
                    user_establishment_role_edit_scope=entry["edit_scope"],
                    user_establishment_role_delete_scope=entry["delete_scope"],
                )
            )
        self.db.commit()
        return self.list_for_user(user_id)
