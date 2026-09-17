from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)


class RegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime