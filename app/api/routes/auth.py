import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security.account_lifecycle import can_authenticate_user
from app.core.security.password import hash_password, verify_password
from app.core.security.jwt import create_access_token
from app.core.security.one_time_token import hash_token
from app.core.rate_limit import (
    is_login_allowed,
    is_login_ip_allowed,
    is_password_recovery_allowed,
    is_password_recovery_ip_allowed,
    is_password_reset_allowed,
    is_registration_code_allowed,
    is_registration_identity_allowed,
    is_registration_ip_allowed,
    RateLimitUnavailable,
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
from app.schemas.employee_registration import (
    EmailVerificationRequest,
    EmployeeRegistrationCreate,
    RegistrationCodeValidate,
    RegistrationCodeValidationResponse,
    RegistrationStatusResponse,
    ResendVerificationRequest,
)
from app.services.account_lifecycle_service import LifecycleTransitionError
from app.services.email.service import EmailDeliveryUnavailable
from app.services.employee_registration_service import (
    create_employee_registration,
    registration_code_is_valid,
    resend_registration_verification,
    send_employee_verification_email,
    verify_registration_email,
)
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
logger = logging.getLogger(__name__)
REGISTRATION_RESPONSE_MESSAGE = (
    "If the information is eligible, your registration request was received."
)


def _client_host(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _enforce_registration_ip_limit(request: Request) -> None:
    try:
        if not is_registration_ip_allowed(
            f"registration-ip:{_client_host(request)}"
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later.",
            )
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable.",
        ) from exc


def _enforce_registration_code_limit(
    raw_code: str,
) -> None:
    try:
        if not is_registration_code_allowed(
            f"registration-code:{hash_token(raw_code)}"
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later.",
            )
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable.",
        ) from exc


def _enforce_registration_identity_limit(
    request: Request,
    email: str,
) -> None:
    try:
        if not is_registration_identity_allowed(
            f"registration-email:{hash_token(email.strip().lower())}"
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification requests. Please try again later.",
            )
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is temporarily unavailable.",
        ) from exc


def _ensure_email_available(email_service: EmailService) -> None:
    try:
        email_service.ensure_available()
    except EmailDeliveryUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured for this environment.",
        ) from exc


def _send_registration_verification_email(
    email_service: EmailService,
    user: User,
    raw_token: str,
) -> None:
    try:
        send_employee_verification_email(
            email_service,
            user,
            raw_token,
        )
    except EmailDeliveryUnavailable as exc:
        logger.error(
            "Employee registration verification email delivery failed (%s)",
            type(exc).__name__,
        )


@router.post(
    "/auth/registration-code/validate",
    response_model=RegistrationCodeValidationResponse,
)
async def validate_registration_code(
    payload: RegistrationCodeValidate,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_registration_ip_limit(request)
    _enforce_registration_code_limit(payload.code)
    return {"valid": registration_code_is_valid(db, payload.code)}


@router.post(
    "/auth/register",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RegistrationStatusResponse,
)
async def register_employee(
    payload: EmployeeRegistrationCreate,
    request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    _ensure_email_available(email_service)
    _enforce_registration_ip_limit(request)
    _enforce_registration_code_limit(payload.organization_code)

    try:
        registration = create_employee_registration(
            db,
            organization_code=payload.organization_code,
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
            employee_id=payload.employee_id,
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            job_title=payload.job_title,
        )
    except LifecycleTransitionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if registration is not None:
        user, raw_token = registration
        _send_registration_verification_email(
            email_service,
            user,
            raw_token,
        )

    return {"message": REGISTRATION_RESPONSE_MESSAGE}


@router.post(
    "/auth/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RegistrationStatusResponse,
)
async def resend_employee_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    _ensure_email_available(email_service)
    _enforce_registration_ip_limit(request)
    _enforce_registration_identity_limit(request, str(payload.email))
    registration = resend_registration_verification(
        db,
        str(payload.email),
    )
    if registration is not None:
        user, raw_token = registration
        _send_registration_verification_email(
            email_service,
            user,
            raw_token,
        )

    return {"message": REGISTRATION_RESPONSE_MESSAGE}


@router.post("/auth/verify-email")
async def verify_employee_email(
    payload: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    try:
        user = verify_registration_email(db, payload.token)
    except LifecycleTransitionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification token.",
        ) from exc
    return {
        "message": "Email verified. Your registration is awaiting approval.",
        "approval_status": user.approval_status,
    }


@router.post("/auth/login")
async def login_user(
    request: Request,
    user: UserLogin,
    db: Session = Depends(get_db),
):

    login_key = f"login:{request.client.host}:{user.email.lower()}"

    login_ip_key = f"login-ip:{request.client.host}"

    identity_allowed = is_login_allowed(login_key)
    ip_allowed = is_login_ip_allowed(login_ip_key)

    if not identity_allowed or not ip_allowed:
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

    if not can_authenticate_user(db_user):
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
    _ensure_email_available(email_service)
    recovery_ip_key = (
        f"password-recovery-ip:{request.client.host}"
    )
    if not is_password_recovery_ip_allowed(recovery_ip_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password recovery attempts. Please try again later.",
        )

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
        try:
            send_password_reset_email(
                db,
                db_user,
                email_service,
            )
            db.commit()
        except EmailDeliveryUnavailable as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password recovery email could not be sent.",
            ) from exc

    return {
        "message": (
            "If an account exists with that email, "
            "a password reset link has been sent."
        ),
    }

@router.post("/auth/reset-password")
async def reset_password_endpoint(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    reset_key = f"password-reset:{request.client.host}"

    if not is_password_reset_allowed(reset_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Please try again later.",
        )

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

    login_ip_key = f"login-ip:{request.client.host}"

    identity_allowed = is_login_allowed(login_key)
    ip_allowed = is_login_ip_allowed(login_ip_key)

    if not identity_allowed or not ip_allowed:
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
    if not can_authenticate_user(db_user):
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

    login_ip_key = f"login-ip:{request.client.host}"

    identity_allowed = is_login_allowed(login_key)
    ip_allowed = is_login_ip_allowed(login_ip_key)

    if not identity_allowed or not ip_allowed:
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
    if not can_authenticate_user(db_user):
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

    login_ip_key = f"login-ip:{request.client.host}"

    identity_allowed = is_login_allowed(login_key)
    ip_allowed = is_login_ip_allowed(login_ip_key)

    if not identity_allowed or not ip_allowed:
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
    if not can_authenticate_user(db_user):
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
