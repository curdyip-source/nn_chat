from typing import Literal, Optional

from pydantic import BaseModel, Field

# Разделы меню, которые можно выдавать не-админу (админ-разделы недоступны через это).
GRANTABLE_SECTIONS = ("orders", "products", "inventory", "registrations", "contacts", "chat", "price")


class EstablishmentPermission(BaseModel):
    # Настройки прав пользователя на конкретном складе. scope: own | establishment.
    establishment_id: int
    view_scope: Literal["own", "establishment"] = "establishment"
    can_create: bool = False
    edit_scope: Literal["none", "own", "establishment"] = "none"
    delete_scope: Literal["none", "own", "establishment"] = "none"


class UserPermissionsPayload(BaseModel):
    # Полный набор складов с настройками. Отсутствие склада = нет доступа к нему.
    establishments: list[EstablishmentPermission] = Field(default_factory=list)


class UserCreatePayload(BaseModel):
    user_login: str = Field(min_length=3, max_length=100)
    user_password: str = Field(min_length=6, max_length=255)
    user_admin: bool = False
    user_active: bool = False
    user_first_name: str = Field(min_length=1, max_length=100)
    user_second_name: str = Field(min_length=1, max_length=100)
    user_profile_photo: Optional[str] = Field(default=None, max_length=2000)
    user_age: int = Field(ge=0, le=150)
    user_address: str = Field(min_length=1, max_length=255)


class BootstrapFirstAdminPayload(UserCreatePayload):
    first_admin_pass: str = Field(min_length=12, max_length=255)


class UserUpdatePayload(BaseModel):
    user_login: Optional[str] = Field(default=None, min_length=3, max_length=100)
    user_password: Optional[str] = Field(default=None, min_length=6, max_length=255)
    user_admin: Optional[bool] = None
    user_active: Optional[bool] = None
    user_first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_second_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_profile_photo: Optional[str] = Field(default=None, max_length=2000)
    user_age: Optional[int] = Field(default=None, ge=0, le=150)
    user_address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    # Разрешённые разделы меню (ось A). None = не менять; список = только эти разделы.
    # Валидация значений — в сервисе update_user (чистый HTTPException).
    user_sections: Optional[list[str]] = None


class UserProfileUpdatePayload(BaseModel):
    user_first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_second_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_profile_photo: Optional[str] = Field(default=None, max_length=2000)
    user_age: Optional[int] = Field(default=None, ge=0, le=150)
    user_address: Optional[str] = Field(default=None, min_length=1, max_length=255)