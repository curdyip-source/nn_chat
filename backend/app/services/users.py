from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.core.audit_types import (
    ENTITY_TYPE_SESSION,
    ENTITY_TYPE_USER,
    EVENT_TYPE_AUTH_LOGIN_SUCCEEDED,
    EVENT_TYPE_USER_BOOTSTRAP,
    EVENT_TYPE_USER_REGISTER,
    EVENT_TYPE_USER_CREATE,
    EVENT_TYPE_USER_DELETE,
    EVENT_TYPE_USER_UPDATE,
)
from app.core.security import hash_password
from app.core.session import generate_session_token, get_session_expires_at
from app.core.tokens import create_access_token
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository
from app.repositories.profile_photos import ProfilePhotoRepository
from app.schemas.auth import RegisterPayload
from app.schemas.common import build_pagination, model_to_dict
from app.schemas.users import UserCreatePayload, UserProfileUpdatePayload, UserUpdatePayload
from app.services.audit import log_audit_event
from app.services.profile_photos import build_profile_photo_storage_key
from app.services.serializers import serialize_datetime, serialize_user


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.profile_photo_repository = ProfilePhotoRepository(db)
        self.session_repository = SessionRepository(db)

    def get_setup_status(self) -> dict:
        users_count = self.repository.count_users()
        return {
            "users_count": users_count,
            "bootstrap_required": users_count == 0,
        }

    def list_users(self, *, search: str | None = None, admin_only: bool | None = None, page: int = 1, page_size: int = 10, sort_by: str = "user_id", sort_order: str = "asc") -> dict:
        rows, total = self.repository.list(search=search, admin_only=admin_only, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)
        return {
            "items": [serialize_user(row) for row in rows],
            "pagination": build_pagination(page, page_size, total),
            "filters": {
                "search": search,
                "admin_only": admin_only,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        }

    def get_user_by_login(self, user_login: str):
        return self.repository.get_by_login(user_login)

    def get_user_by_id_or_401(self, user_id: int) -> dict:
        row = self.repository.get_by_id(user_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
        if not row.user_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь деактивирован")
        return serialize_user(row)

    def get_user_by_id_or_404(self, user_id: int):
        row = self.repository.get_by_id(user_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
        return row

    def ensure_login_is_unique(self, user_login: str, exclude_user_id: int | None = None) -> None:
        existing_user = self.repository.get_by_login(user_login)
        if existing_user is None:
            return
        if exclude_user_id is not None and existing_user.user_id == exclude_user_id:
            return
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Логин уже занят")

    def prepare_user_create_data(self, payload: UserCreatePayload) -> dict:
        return {
            "user_login": payload.user_login,
            "user_password": hash_password(payload.user_password),
            "user_admin": payload.user_admin,
            "user_active": payload.user_active,
            "user_first_name": payload.user_first_name,
            "user_second_name": payload.user_second_name,
            "user_profile_photo": payload.user_profile_photo,
            "user_age": payload.user_age,
            "user_address": payload.user_address,
        }

    def bootstrap_first_user(self, payload: UserCreatePayload) -> dict:
        if self.repository.count_users() > 0:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Первый пользователь уже создан")
        self.ensure_login_is_unique(payload.user_login)
        create_data = self.prepare_user_create_data(payload)
        create_data["user_active"] = True
        row = self.repository.create(create_data, force_admin=True)
        row = self.repository.update(row, {"user_verified_user_id": row.user_id})
        refresh_token = generate_session_token()
        refresh_expires_at = get_session_expires_at()
        refresh_session = self.session_repository.create(token=refresh_token, user_id=row.user_id, expires_at=refresh_expires_at)
        access_token, access_expires_at = create_access_token(session_id=refresh_session.session_id, user_id=row.user_id)
        log_audit_event(
            self.db,
            actor_user_id=row.user_id,
            entity_type=ENTITY_TYPE_USER,
            entity_id=row.user_id,
            event_type=EVENT_TYPE_USER_BOOTSTRAP,
            event_payload={"user_login": row.user_login, "user_admin": row.user_admin},
        )
        log_audit_event(
            self.db,
            actor_user_id=row.user_id,
            entity_type=ENTITY_TYPE_SESSION,
            entity_id=refresh_session.session_id,
            event_type=EVENT_TYPE_AUTH_LOGIN_SUCCEEDED,
            event_payload={"user_id": row.user_id, "bootstrap": True},
        )
        return {
            "user": serialize_user(row),
            "token": access_token,
            "access_token": access_token,
            "access_expires_at": serialize_datetime(access_expires_at),
            "refresh_token": refresh_session.session_token,
            "refresh_expires_at": serialize_datetime(refresh_session.session_expires_at),
        }

    def create_user(self, payload: UserCreatePayload, actor_user: dict) -> dict:
        self.ensure_login_is_unique(payload.user_login)
        row = self.repository.create(self.prepare_user_create_data(payload))
        if row.user_active:
            row = self.repository.update(row, {"user_verified_user_id": actor_user["user_id"]})
        log_audit_event(
            self.db,
            actor_user_id=actor_user["user_id"],
            entity_type=ENTITY_TYPE_USER,
            entity_id=row.user_id,
            event_type=EVENT_TYPE_USER_CREATE,
            event_payload={"user_login": row.user_login, "user_admin": row.user_admin},
        )
        return serialize_user(row)

    def register_user(self, payload: RegisterPayload) -> dict:
        self.ensure_login_is_unique(payload.user_login)
        row = self.repository.create(
            {
                "user_login": payload.user_login,
                "user_password": hash_password(payload.user_password),
                "user_admin": False,
                "user_active": False,
                "user_first_name": payload.user_first_name,
                "user_second_name": payload.user_second_name,
                "user_profile_photo": None,
                "user_age": 0,
                "user_address": "-",
            }
        )
        log_audit_event(
            self.db,
            actor_user_id=row.user_id,
            entity_type=ENTITY_TYPE_USER,
            entity_id=row.user_id,
            event_type=EVENT_TYPE_USER_REGISTER,
            event_payload={"user_login": row.user_login, "user_active": row.user_active},
        )
        return {
            "message": "Пользователь зарегистрирован и ожидает активации",
            "user": serialize_user(row),
        }

    def update_user(self, user_id: int, payload: UserUpdatePayload, actor_user: dict) -> dict:
        user = self.get_user_by_id_or_404(user_id)
        data = model_to_dict(payload)
        if "user_login" in data:
            self.ensure_login_is_unique(data["user_login"], exclude_user_id=user_id)
        if "user_password" in data:
            data["user_password"] = hash_password(data["user_password"])
        if "user_active" in data:
            data["user_verified_user_id"] = actor_user["user_id"] if data["user_active"] else None
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")
        row = self.repository.update(user, data)
        log_audit_event(
            self.db,
            actor_user_id=actor_user["user_id"],
            entity_type=ENTITY_TYPE_USER,
            entity_id=row.user_id,
            event_type=EVENT_TYPE_USER_UPDATE,
            event_payload={"changed_fields": sorted(data.keys())},
        )
        return serialize_user(row)

    def update_profile(self, user_id: int, payload: UserProfileUpdatePayload) -> dict:
        user = self.get_user_by_id_or_404(user_id)
        data = model_to_dict(payload)
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")

        if "user_profile_photo" in data and data["user_profile_photo"] != build_profile_photo_storage_key(user_id):
            self.profile_photo_repository.delete_for_user(user_id)

        row = self.repository.update(user, data)
        return serialize_user(row)

    def delete_user(self, user_id: int, current_user: dict) -> dict:
        user = self.get_user_by_id_or_404(user_id)
        if current_user["user_id"] == user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить самого себя")
        if user.user_admin and self.repository.count_admins() <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить последнего администратора")
        deleted_payload = {
            "user_login": user.user_login,
            "user_admin": user.user_admin,
        }
        self.session_repository.delete_for_user(user_id)
        self.repository.delete(user)
        log_audit_event(
            self.db,
            actor_user_id=current_user["user_id"],
            entity_type=ENTITY_TYPE_USER,
            entity_id=user_id,
            event_type=EVENT_TYPE_USER_DELETE,
            event_payload=deleted_payload,
        )
        return {"message": "Пользователь удален"}


def get_setup_status(db: Session) -> dict:
    return UserService(db).get_setup_status()


def list_users(db: Session, *, search: str | None = None, admin_only: bool | None = None, page: int = 1, page_size: int = 10, sort_by: str = "user_id", sort_order: str = "asc") -> dict:
    return UserService(db).list_users(search=search, admin_only=admin_only, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)


def get_user_by_login(db: Session, user_login: str):
    return UserService(db).get_user_by_login(user_login)


def get_user_by_id_or_401(db: Session, user_id: int) -> dict:
    return UserService(db).get_user_by_id_or_401(user_id)


def bootstrap_first_user(db: Session, payload: UserCreatePayload) -> dict:
    return UserService(db).bootstrap_first_user(payload)


def create_user(db: Session, payload: UserCreatePayload, actor_user: dict) -> dict:
    return UserService(db).create_user(payload, actor_user)


def register_user(db: Session, payload: RegisterPayload) -> dict:
    return UserService(db).register_user(payload)


def update_user(db: Session, user_id: int, payload: UserUpdatePayload, actor_user: dict) -> dict:
    return UserService(db).update_user(user_id, payload, actor_user)


def update_user_profile(db: Session, user_id: int, payload: UserProfileUpdatePayload) -> dict:
    return UserService(db).update_profile(user_id, payload)


def delete_user(db: Session, user_id: int, current_user: dict) -> dict:
    return UserService(db).delete_user(user_id, current_user)