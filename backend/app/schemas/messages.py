from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class MessageAttachmentCreatePayload(BaseModel):
    attachment_kind: Literal["photo", "file"]
    attachment_original_filename: str = Field(min_length=1, max_length=255)
    attachment_mime_type: str = Field(min_length=1, max_length=150)
    attachment_storage_key: str = Field(min_length=1, max_length=255)
    attachment_size_bytes: Optional[int] = Field(default=None, ge=0)


class MessageCreatePayload(BaseModel):
    message_type: Literal["message", "file"]
    message_text: Optional[str] = Field(default=None, max_length=4000)
    attachments: list[MessageAttachmentCreatePayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_message(self):
        if self.message_type == "message" and not (self.message_text and self.message_text.strip()):
            raise ValueError("Текст сообщения обязателен")
        if self.message_type == "file" and not self.attachments:
            raise ValueError("Для файлового сообщения нужно хотя бы одно вложение")
        return self


class MessageUpdatePayload(BaseModel):
    message_text: str = Field(min_length=1, max_length=4000)