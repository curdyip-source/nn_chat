from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import PROFILE_PHOTO_MAX_BYTES
from app.repositories.profile_photos import ProfilePhotoRepository
from app.repositories.users import UserRepository
from app.services.serializers import serialize_user


ALLOWED_PROFILE_PHOTO_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/webp",
}


@dataclass
class ProfilePhotoContent:
    content: bytes
    mime_type: str


def build_profile_photo_storage_key(user_id: int) -> str:
    return f"profile-photos/{user_id}"


def upload_profile_photo(db: Session, user_id: int, *, mime_type: str, content: bytes) -> dict:
    if mime_type not in ALLOWED_PROFILE_PHOTO_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Поддерживаются только изображения JPEG, PNG, HEIC, HEIF или WEBP")

    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл изображения пустой")

    if len(content) > PROFILE_PHOTO_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Фото профиля слишком большое")

    user_repository = UserRepository(db)
    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    ProfilePhotoRepository(db).upsert(user_id=user_id, mime_type=mime_type, content=content)
    row = user_repository.update(user, {"user_profile_photo": build_profile_photo_storage_key(user_id)})
    return serialize_user(row)


def get_profile_photo_content(db: Session, user_id: int) -> ProfilePhotoContent:
    row = ProfilePhotoRepository(db).get_by_user_id(user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото профиля не найдено")
    return ProfilePhotoContent(content=row.profile_photo_bytes, mime_type=row.profile_photo_mime_type)