from pydantic import BaseModel, Field


class MessageAttachmentUploadResponse(BaseModel):
    attachment_kind: str
    attachment_original_filename: str = Field(min_length=1, max_length=255)
    attachment_mime_type: str = Field(min_length=1, max_length=150)
    attachment_storage_key: str = Field(min_length=1, max_length=255)
    attachment_size_bytes: int = Field(ge=0)