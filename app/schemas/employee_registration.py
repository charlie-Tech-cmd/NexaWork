from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class EmployeeRegistrationCreate(BaseModel):
    organization_code: str = Field(min_length=20, max_length=128)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    employee_id: str = Field(min_length=2, max_length=50)
    branch_id: int = Field(gt=0)
    department_id: int = Field(gt=0)
    job_title: str = Field(min_length=2, max_length=255)

    @field_validator("full_name", "employee_id", "job_title")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class RegistrationCodeValidate(BaseModel):
    code: str = Field(min_length=20, max_length=128)


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=20, max_length=128)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class RegistrationCodeCreate(BaseModel):
    expires_in_days: int | None = Field(default=30, ge=1, le=365)


class RegistrationCodeResponse(BaseModel):
    code: str
    expires_at: datetime | None


class RegistrationStatusResponse(BaseModel):
    message: str


class RegistrationCodeValidationResponse(BaseModel):
    valid: bool
