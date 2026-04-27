from sqlalchemy.orm import Session

from app.repositories.user_devices import UserDeviceRepository
from app.schemas.devices import UserDeviceRegisterPayload


def register_user_device(db: Session, payload: UserDeviceRegisterPayload, current_user: dict) -> dict:
    row = UserDeviceRepository(db).register(user_id=current_user["user_id"], token=payload.user_device_token, platform=payload.user_device_platform)
    return {
        "user_device_id": row.user_device_id,
        "user_device_platform": row.user_device_platform,
        "user_device_is_active": row.user_device_is_active,
    }