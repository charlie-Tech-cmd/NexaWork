from datetime import datetime
from uuid import UUID
from app.schemas.attachment import AttachmentResponse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DirectConversationCreate(BaseModel):
    recipient_user_id: int = Field(gt=0)


class GroupConversationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    member_user_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name cannot be blank")
        return value

    @field_validator("member_user_ids")
    @classmethod
    def validate_member_ids(cls, value: list[int]) -> list[int]:
        if any(user_id <= 0 for user_id in value):
            raise ValueError("Member IDs must be positive integers")
        if len(value) != len(set(value)):
            raise ValueError("Member IDs must not contain duplicates")
        return value


class MessageCreate(BaseModel):
    attachment_ids: list[int] = Field(default_factory=list, max_length=10)
    client_message_id: UUID | None = None

    @field_validator("attachment_ids")
    @classmethod
    def validate_attachments(cls, values):
        if any(v <= 0 for v in values) or len(set(values)) != len(values):
            raise ValueError("Attachment IDs must be distinct positive IDs")
        return values

    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message body cannot be blank")
        return value


class ConversationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    role: Literal["member", "admin"]
    is_active: bool
    joined_at: datetime
    last_read_at: datetime | None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    conversation_type: Literal["direct", "group"]
    name: str | None
    created_by_user_id: int
    created_at: datetime


class MessageResponse(BaseModel):
    attachments: list[AttachmentResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int
    body: str
    created_at: datetime
    edited_at: datetime | None


class MessagePage(BaseModel):
    items: list[MessageResponse]
    next_cursor: int | None


class MessagingPerson(BaseModel):
    id: int
    full_name: str


class ConversationSummary(ConversationResponse):
    members: list[MessagingPerson] = Field(default_factory=list)


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None
