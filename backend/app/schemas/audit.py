from typing import Any

from pydantic import BaseModel, Field


class AuditEventCreatePayload(BaseModel):
    actor_user_id: int | None = None
    entity_type: str = Field(min_length=2, max_length=100)
    entity_id: int | None = None
    event_type: str = Field(min_length=3, max_length=100)
    event_payload: dict[str, Any] | None = None
    request_id: str | None = Field(default=None, max_length=64)
    ip_address: str | None = Field(default=None, max_length=64)
    user_agent: str | None = None