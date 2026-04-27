from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.devices import UserDeviceRegisterPayload
from app.services.user_devices import register_user_device

router = APIRouter(prefix="/user-devices", tags=["user-devices"])


@router.post("", status_code=status.HTTP_201_CREATED)
def register_user_device_route(payload: UserDeviceRegisterPayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": register_user_device(db, payload, current_user)}