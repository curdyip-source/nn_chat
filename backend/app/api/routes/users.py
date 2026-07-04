from secrets import compare_digest

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import FIRST_ADMIN_PASS
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.users import BootstrapFirstAdminPayload, UserCreatePayload, UserPermissionProfilePayload, UserProfileUpdatePayload, UserUpdatePayload
from app.services.profile_photos import upload_profile_photo
from app.services.users import UserService, bootstrap_first_user, create_user, delete_user, list_chat_participants, list_users, set_user_permission_profile, update_user, update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/participants")
def get_chat_participants(_: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return list_chat_participants(db)


@router.get("")
def get_users(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    admin_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    sort_by: str = Query(default="user_id"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> dict:
    return list_users(db, search=search, admin_only=admin_only, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_user(payload: BootstrapFirstAdminPayload, db: Session = Depends(get_db)) -> dict:
    if UserService(db).get_setup_status()["users_count"] > 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Первый пользователь уже создан")
    if not FIRST_ADMIN_PASS:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bootstrap первого администратора не настроен")
    if not compare_digest(payload.first_admin_pass, FIRST_ADMIN_PASS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный ключ первого администратора")
    return bootstrap_first_user(db, UserCreatePayload(**payload.model_dump(exclude={"first_admin_pass"})))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user_route(payload: UserCreatePayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": create_user(db, payload, current_user)}


@router.put("/{user_id}")
def update_user_route(user_id: int, payload: UserUpdatePayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": update_user(db, user_id, payload, current_user)}


@router.put("/{user_id}/permission-profile")
def set_user_permission_profile_route(user_id: int, payload: UserPermissionProfilePayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": set_user_permission_profile(db, user_id, payload, current_user)}


@router.delete("/{user_id}")
def delete_user_route(user_id: int, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return delete_user(db, user_id, current_user)


@router.put("/me/profile")
def update_my_profile(payload: UserProfileUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_user_profile(db, current_user["user_id"], payload)}


@router.post("/me/profile-photo")
async def upload_my_profile_photo(file: UploadFile = File(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {
        "item": upload_profile_photo(
            db,
            current_user["user_id"],
            mime_type=(file.content_type or "").strip().lower(),
            content=await file.read(),
        )
    }