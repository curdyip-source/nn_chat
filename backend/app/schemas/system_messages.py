from typing import Literal

from pydantic import BaseModel, Field


class SystemMessageCreatePayload(BaseModel):
    # all — все активные пользователи на момент отправки; user/users — по явному
    # списку user_ids (user — ровно один id, users — один или больше).
    text: str = Field(min_length=1, max_length=2000)
    important: bool = False
    target: Literal["all", "user", "users"]
    user_ids: list[int] = Field(default_factory=list)
