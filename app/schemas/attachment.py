from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    message_id: int | None
    uploaded_by_user_id: int
    filename: str
    content_type: str
    size_bytes: int
    status: Literal["uploading", "ready", "attached", "deleting", "deleted"]
    created_at: datetime
    deleted_at: datetime | None


class AttachmentPage(BaseModel):
    items: list[AttachmentResponse]
    next_cursor: int | None
