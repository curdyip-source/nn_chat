from sqlalchemy.orm import Session

from app.models.profile_photos import ProfilePhoto


class ProfilePhotoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_id(self, user_id: int) -> ProfilePhoto | None:
        return self.db.query(ProfilePhoto).filter(ProfilePhoto.profile_photo_user_id == user_id).first()

    def upsert(self, *, user_id: int, mime_type: str, content: bytes) -> ProfilePhoto:
        existing = self.get_by_user_id(user_id)
        if existing is not None:
            existing.profile_photo_mime_type = mime_type
            existing.profile_photo_bytes = content
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = ProfilePhoto(profile_photo_user_id=user_id, profile_photo_mime_type=mime_type, profile_photo_bytes=content)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_for_user(self, user_id: int) -> None:
        row = self.get_by_user_id(user_id)
        if row is None:
            return
        self.db.delete(row)
        self.db.commit()