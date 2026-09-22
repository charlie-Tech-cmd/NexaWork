from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    user_id: int
    employee_id: str = Field(min_length=2, max_length=50)
    branch_id: int
    department_id: int
    job_title: str = Field(min_length=2, max_length=255)
    profile_picture: str | None = Field(
        default=None,
        max_length=500,
    )


class EmployeeUpdate(BaseModel):
    employee_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )
    branch_id: int | None = None
    department_id: int | None = None
    job_title: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )
    profile_picture: str | None = Field(
        default=None,
        max_length=500,
    )
    is_active: bool | None = None

class EmployeeLogin(BaseModel):
    employee_id: str
    password: str


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    employee_id: str
    branch_id: int
    department_id: int
    job_title: str
    profile_picture: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime