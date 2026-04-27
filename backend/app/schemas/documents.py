from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreatePayload(BaseModel):
    document_kind: str = Field(min_length=1, max_length=100)
    document_original_filename: str = Field(min_length=1, max_length=255)
    document_mime_type: str = Field(min_length=1, max_length=150)
    document_storage_key: str = Field(min_length=1, max_length=255)
    document_note: Optional[str] = Field(default=None, max_length=2000)
    document_size_bytes: Optional[int] = Field(default=None, ge=0)


class DocumentUpdatePayload(BaseModel):
    document_status: Optional[str] = Field(default=None, min_length=1, max_length=50)
    document_note: Optional[str] = Field(default=None, max_length=2000)