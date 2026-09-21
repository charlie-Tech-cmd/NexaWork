from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.user import UserResponse


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationOnboardingCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: str = Field(min_length=2, max_length=100)
    admin_email: str
    admin_password: str
    admin_confirm_password: str
    admin_full_name: str = Field(min_length=2, max_length=255)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.admin_password != self.admin_confirm_password:
            raise ValueError("Passwords do not match")
        return self


class OrganizationOnboardingResponse(BaseModel):
    organization: OrganizationResponse
    admin: UserResponse
