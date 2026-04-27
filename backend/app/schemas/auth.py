from pydantic import BaseModel, Field


class LoginPayload(BaseModel):
    user_login: str = Field(min_length=3, max_length=100)
    user_password: str = Field(min_length=6, max_length=255)


class RegisterPayload(BaseModel):
    user_login: str = Field(min_length=3, max_length=100)
    user_password: str = Field(min_length=6, max_length=255)
    user_first_name: str = Field(min_length=1, max_length=100)
    user_second_name: str = Field(min_length=1, max_length=100)


class RefreshTokenPayload(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=255)