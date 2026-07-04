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

    def replace_for_user(self, user_id: int, establishment_ids: list[int]) -> list[UserEstablishmentRole]:
        # Полная замена набора складов-членств пользователя. Удаляем через ORM-объекты
        # (а не bulk delete), чтобы identity map оставалась консистентной — иначе
        # переиспользование PK в SQLite даёт устаревшее чтение.
        for existing in self.list_for_user(user_id):
            self.db.delete(existing)
        self.db.flush()
        for establishment_id in dict.fromkeys(establishment_ids):  # уникальные, порядок сохранён
            self.db.add(
                UserEstablishmentRole(
                    user_establishment_role_user_id=user_id,
                    user_establishment_role_establishment_id=establishment_id,
                )
            )
        self.db.commit()
        return self.list_for_user(user_id)
