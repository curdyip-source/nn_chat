from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models.users import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_users(self) -> int:
        return self.db.query(User).count()

    def count_admins(self) -> int:
        return self.db.query(User).filter(User.user_admin.is_(True)).count()

    def get_by_login(self, user_login: str) -> User | None:
        return self.db.query(User).filter(User.user_login == user_login).first()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def list_active(self) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.user_active.is_(True))
            .order_by(asc(User.user_second_name), asc(User.user_first_name), asc(User.user_id))
            .all()
        )

    def list_active_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        return (
            self.db.query(User)
            .filter(User.user_active.is_(True), User.user_id.in_(user_ids))
            .all()
        )

    def list(self, *, search: str | None = None, admin_only: bool | None = None, page: int = 1, page_size: int = 10, sort_by: str = "user_id", sort_order: str = "asc") -> tuple[list[User], int]:
        query = self.db.query(User)

        if search:
            like_value = f"%{search}%"
            query = query.filter(
                or_(
                    User.user_login.ilike(like_value),
                    User.user_first_name.ilike(like_value),
                    User.user_second_name.ilike(like_value),
                    User.user_address.ilike(like_value),
                )
            )

        if admin_only is not None:
            query = query.filter(User.user_admin.is_(admin_only))

        order_mapping = {
            "user_id": User.user_id,
            "user_login": User.user_login,
            "user_active": User.user_active,
            "user_age": User.user_age,
            "user_first_name": User.user_first_name,
            "user_created_at": User.user_created_at,
        }
        order_column = order_mapping.get(sort_by, User.user_id)
        order_fn = desc if sort_order == "desc" else asc

        total = query.count()
        items = (
            query.order_by(order_fn(order_column), order_fn(User.user_id))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, user_data: dict, force_admin: bool = False) -> User:
        user = User(
            **{
                **user_data,
                "user_admin": True if force_admin else user_data["user_admin"],
            }
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, data: dict) -> User:
        for field_name, field_value in data.items():
            setattr(user, field_name, field_value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()