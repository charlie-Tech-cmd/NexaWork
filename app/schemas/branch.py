from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)


class BranchUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    is_active: bool | None = None


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region_id: int
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime