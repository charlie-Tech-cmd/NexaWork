from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security.password import hash_password, verify_password
from app.core.security.jwt import create_access_token
from app.core.rate_limit import (
    is_login_allowed,
    is_password_recovery_allowed,
)
from app.db.session import get_db
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles
from app.schemas.employee import EmployeeLogin
from app.services.password_reset_service import reset_password
from app.schemas.user import (
    AdminLogin,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserLogin,
    UserResponse,
)
from app.api.dependencies_email import get_email_service
from app.services.email.service import EmailService
from app.services.password_recovery_service import (
    send_password_reset_email,
)


router = APIRouter(prefix="/api/v1")


@router.post("/auth/login")
async def login_user(
    request: Request,
    user: UserLogin,
    db: Session = Depends(get_db),
):

    login_key = f"login:{request.client.host}:{user.email.lower()}"

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    db_user = db.scalar(
        select(User).where(User.email == user.email)
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    password_valid = verify_password(
        user.password,
        db_user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    organization = db.scalar(
        select(Organization).where(
            Organization.id == db_user.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive or unavailable",
        )

    access_token = create_access_token(
        str(db_user.id),
        token_version=db_user.token_version,
    )

    return {
        "message": "Login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "access_token": access_token,
    }


@router.post("/auth/forgot-password")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    recovery_key = (
        f"password-recovery:{request.client.host}:"
        f"{payload.email.lower()}"
    )

    if not is_password_recovery_allowed(recovery_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password recovery attempts. Please try again later.",
        )

    db_user = db.scalar(
        select(User).where(
            User.email == payload.email,
        )
    )

    if db_user is not None and db_user.is_active:
        send_password_reset_email(
            db,
            db_user,
            email_service,
        )
        db.commit()

    return {
        "message": (
            "If an account exists with that email, "
            "a password reset link has been sent."
        ),
    }

@router.post("/auth/reset-password")
async def reset_password_endpoint(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        reset_password(
            db,
            payload.token,
            payload.new_password,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "message": "Password reset successful",
    }


@router.post("/auth/employee/login")
async def employee_login(
    request: Request,
    employee_login: EmployeeLogin,
    db: Session = Depends(get_db),
):

    login_key = (
        f"employee-login:{request.client.host}:"
        f"{employee_login.employee_id.lower()}"
    )

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    employee = db.scalar(
        select(Employee).where(
            Employee.employee_id == employee_login.employee_id,
            Employee.is_active.is_(True),
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    db_user = db.scalar(
        select(User).where(
            User.id == employee.user_id,
            User.is_active.is_(True),
        )
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    password_valid = verify_password(
        employee_login.password,
        db_user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    organization = db.scalar(
        select(Organization).where(
            Organization.id == db_user.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive or unavailable",
        )

    access_token = create_access_token(
        str(db_user.id),
        token_version=db_user.token_version,
    )

    return {
        "message": "Login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "employee_id": employee.employee_id,
        "access_token": access_token,
    }


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post("/auth/admin/login")
async def admin_login(
    request: Request,
    admin_login: AdminLogin,
    db: Session = Depends(get_db),
):

    login_key = (
        f"admin-login:{request.client.host}:"
        f"{admin_login.email.lower()}"
    )

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    db_user = db.scalar(
        select(User).where(
            User.email == admin_login.email,
            User.is_active.is_(True),
        )
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(
        admin_login.password,
        db_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    organization = db.scalar(
        select(Organization).where(
            Organization.id == db_user.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive or unavailable",
        )

    admin_role_exists = db.scalar(
        select(Role.id)
        .join(
            user_roles,
            user_roles.c.role_id == Role.id,
        )
        .join(
            role_permissions,
            role_permissions.c.role_id == Role.id,
        )
        .join(
            Permission,
            Permission.id == role_permissions.c.permission_id,
        )
        .where(
            user_roles.c.user_id == db_user.id,
            Role.organization_id == db_user.organization_id,
            Role.is_active.is_(True),
            Permission.name == "ADMIN_ACCESS",
            Permission.is_active.is_(True),
        )
    )

    if admin_role_exists is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    access_token = create_access_token(
        str(db_user.id),
        auth_type="admin",
        token_version=db_user.token_version,

    )

    return {
        "message": "Admin login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "access_token": access_token,
    }


@router.post("/auth/super-admin/login")
async def super_admin_login(
    request: Request,
    super_admin_login: AdminLogin,
    db: Session = Depends(get_db),
):
    login_key = (
        f"super-admin-login:{request.client.host}:"
        f"{super_admin_login.email.lower()}"
    )

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    db_user = db.scalar(
        select(User).where(
            User.email == super_admin_login.email,
            User.is_active.is_(True),
            User.is_super_admin.is_(True),
            User.organization_id.is_(None),
        )
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(
        super_admin_login.password,
        db_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        str(db_user.id),
        auth_type="super_admin",
        token_version=db_user.token_version,

    )

    return {
        "message": "Super Admin login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "access_token": access_token,
    }
