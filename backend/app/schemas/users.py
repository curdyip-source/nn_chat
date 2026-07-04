from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserPermissionProfilePayload(BaseModel):
    # Членство: в каких складах работает пользователь.
    establishment_ids: list[int] = Field(default_factory=list)
    # Профиль прав (действует в рамках членств). scope: own | establishment | all.
    view_scope: Literal["own", "establishment", "all"] = "establishment"
    can_create: bool = False
    edit_scope: Literal["none", "own", "establishment", "all"] = "none"
    delete_scope: Literal["none", "own", "establishment", "all"] = "none"


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


class UserProfileUpdatePayload(BaseModel):
    user_first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_second_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    user_profile_photo: Optional[str] = Field(default=None, max_length=2000)
    user_age: Optional[int] = Field(default=None, ge=0, le=150)
    user_address: Optional[str] = Field(default=None, min_length=1, max_length=255)