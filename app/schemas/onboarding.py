from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationRegistrationCodeCreate(BaseModel):
    expires_in_minutes: int | None = Field(default=None, gt=0, le=525600)


class OrganizationRegistrationCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    code: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class OrganizationRegistrationCodeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    is_active: bool
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class EmployeeRegistrationRequestCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    job_title: str = Field(min_length=2, max_length=255)
    branch_id: int
    department_id: int
    registration_code: str = Field(min_length=6, max_length=64)


class RegistrationStructureRequest(BaseModel):
    registration_code: str = Field(min_length=6, max_length=64)


class ResendRegistrationVerificationRequest(BaseModel):
    registration_code: str = Field(min_length=6, max_length=64)
    email: EmailStr = Field(max_length=255)


class RegistrationStructureDepartment(BaseModel):
    id: int
    name: str


class RegistrationStructureBranch(BaseModel):
    id: int
    name: str
    departments: list[RegistrationStructureDepartment]


class RegistrationStructureResponse(BaseModel):
    branches: list[RegistrationStructureBranch]


class EmployeeRegistrationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    email: EmailStr
    full_name: str
    employee_id: str | None = None
    branch_id: int
    department_id: int
    job_title: str
    email_verification_status: str
    approval_status: str
    account_status: str
    approval_reason: str | None
    created_at: datetime


class EmployeeApprovalAction(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class EmployeeInvitationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr = Field(max_length=255)
    job_title: str = Field(min_length=2, max_length=255)
    branch_id: int
    department_id: int
    expires_in_minutes: int = Field(default=1440, gt=0, le=43200)


class EmployeeInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    email: EmailStr
    full_name: str
    branch_id: int
    department_id: int
    job_title: str
    status: str
    expires_at: datetime | None
    created_at: datetime


class EmployeeInvitationAcceptanceResponse(EmployeeInvitationResponse):
    employee_id: str


class EmployeeInvitationLinkResponse(EmployeeInvitationResponse):
    acceptance_url: str


class InvitationAcceptanceRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=255)


class EmailVerificationRequest(BaseModel):
    token: str


class AccountStatusUpdate(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class EmployeeAccountResponse(BaseModel):
    id: int
    organization_id: int
    employee_id: str
    email: EmailStr
    full_name: str
    branch_id: int
    department_id: int
    job_title: str
    email_verification_status: str
    approval_status: str
    account_status: str
    approval_reason: str | None
    account_status_reason: str | None
    created_at: datetime
