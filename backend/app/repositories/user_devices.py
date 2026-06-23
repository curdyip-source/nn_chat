from sqlalchemy.orm import Session

from app.models.user_devices import UserDevice


class UserDeviceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_token(self, token: str) -> UserDevice | None:
        return self.db.query(UserDevice).filter(UserDevice.user_device_token == token).first()

    def register(self, *, user_id: int, token: str, platform: str, environment: str) -> UserDevice:
        existing = self.get_by_token(token)
        if existing is not None:
            existing.user_device_user_id = user_id
            existing.user_device_platform = platform
            existing.user_device_environment = environment
            existing.user_device_is_active = True
            self.db.commit()
            self.db.refresh(existing)
            return existing
        row = UserDevice(user_device_user_id=user_id, user_device_token=token, user_device_platform=platform, user_device_environment=environment, user_device_is_active=True)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def deactivate_token(self, token: str) -> None:
        existing = self.get_by_token(token)
        if existing is None:
            return
        existing.user_device_is_active = False
        self.db.commit()

    def list_active_for_other_users(self, *, excluded_user_id: int) -> list[UserDevice]:
        return (
            self.db.query(UserDevice)
            .filter(UserDevice.user_device_is_active.is_(True), UserDevice.user_device_user_id != excluded_user_id)
            .all()
        )

    def list_active_for_users(self, *, user_ids: list[int]) -> list[UserDevice]:
        if not user_ids:
            return []
        return (
            self.db.query(UserDevice)
            .filter(UserDevice.user_device_is_active.is_(True), UserDevice.user_device_user_id.in_(user_ids))
            .all()
        )