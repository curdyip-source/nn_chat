from typing import Literal

from pydantic import BaseModel, Field


class UserDeviceRegisterPayload(BaseModel):
    user_device_token: str = Field(min_length=1, max_length=255)
    user_device_platform: Literal["ios"]