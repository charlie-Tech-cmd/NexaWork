from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.messaging import MessagingPerson


class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    visibility: Literal["public", "private"]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Channel name cannot be blank")
        return value


class ChannelMemberAdd(BaseModel):
    user_id: int = Field(gt=0)


class ChannelMemberRoleUpdate(BaseModel):
    role: Literal["member", "moderator"]


class ChannelMemberResponse(BaseModel):
    user_id: int
    full_name: str
    role: Literal["member", "moderator"]
    joined_at: datetime


class ChannelSummary(BaseModel):
    id: int
    name: str
    visibility: Literal["public", "private"]
    is_member: bool
    membership_role: Literal["member", "moderator"] | None
    member_count: int
    members: list[MessagingPerson] = Field(default_factory=list)
    created_by_user_id: int
    created_at: datetime


class ChannelPage(BaseModel):
    items: list[ChannelSummary]
    can_create: bool


class ChannelConversation(ChannelSummary):
    organization_id: int
    conversation_type: Literal["channel"] = "channel"


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("title", "body")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Announcement content cannot be blank")
        return value


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    body: str
    created_by_user_id: int
    author_name: str
    created_at: datetime


class AnnouncementPage(BaseModel):
    items: list[AnnouncementResponse]
    can_publish: bool
    next_cursor: int | None
