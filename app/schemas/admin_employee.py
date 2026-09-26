from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminEmployeeCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)

    employee_id: str = Field(
        min_length=2,
        max_length=50,
    )

    branch_id: int
    department_id: int

    job_title: str = Field(
        min_length=2,
        max_length=255,
    )

    role_ids: list[int] = Field(default_factory=list)

class AdminEmployeeUpdate(BaseModel):
    full_name: str | None = None
    branch_id: int | None = None
    department_id: int | None = None
    job_title: str | None = None
    is_active: bool | None = None


class AdminEmployeeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    employee_id: str
    job_title: str
    profile_picture: str | None
    is_active: bool
    created_at: datetime