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

    def replace_for_user(self, user_id: int, roles: list[tuple[int, str]]) -> list[UserEstablishmentRole]:
        # Полная замена набора ролей пользователя: удаляем прежние и вставляем новые.
        # roles — список (establishment_id, role). Дубли по складу схлопываются (последний
        # выигрывает), т.к. уникальность (user, establishment) гарантирована констрейнтом.
        # Удаляем через ORM-объекты (а не bulk delete), чтобы identity map оставалась
        # консистентной — иначе переиспользование PK даёт устаревшее чтение.
        for existing in self.list_for_user(user_id):
            self.db.delete(existing)
        self.db.flush()
        deduped: dict[int, str] = {}
        for establishment_id, role in roles:
            deduped[establishment_id] = role
        for establishment_id, role in deduped.items():
            self.db.add(
                UserEstablishmentRole(
                    user_establishment_role_user_id=user_id,
                    user_establishment_role_establishment_id=establishment_id,
                    user_establishment_role_role=role,
                )
            )
        self.db.commit()
        return self.list_for_user(user_id)
