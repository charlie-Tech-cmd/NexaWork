from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    full_name: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    full_name: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None

class UserDeactivate(BaseModel):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool