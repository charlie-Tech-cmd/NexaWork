from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security.one_time_token import (
    generate_secure_token,
    hash_token,
)
from app.core.security.password import hash_password
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.department import Department
from app.models.email_verification_token import EmailVerificationToken
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.organization_registration_code import (
    OrganizationRegistrationCode,
)
from app.models.region import Region
from app.models.user import User
from app.services.password_reset_service import ensure_utc
from app.services.account_lifecycle_service import LifecycleTransitionError
from app.services.email.service import EmailService
from app.services.email.templates.employee_verification import (
    build_employee_verification_email,
)


def _active_registration_code(
    db: Session,
    raw_code: str,
    now: datetime,
) -> OrganizationRegistrationCode | None:
    registration_code = db.scalar(
        select(OrganizationRegistrationCode)
        .join(
            Organization,
            Organization.id == OrganizationRegistrationCode.organization_id,
        )
        .where(
            OrganizationRegistrationCode.code_hash == hash_token(raw_code),
            OrganizationRegistrationCode.revoked_at.is_(None),
            Organization.is_active.is_(True),
        )
    )
    if registration_code is None:
        return None
    if (
        registration_code.expires_at is not None
        and ensure_utc(registration_code.expires_at) <= now
    ):
        return None
    return registration_code


def registration_code_is_valid(db: Session, raw_code: str) -> bool:
    return _active_registration_code(
        db,
        raw_code,
        datetime.now(timezone.utc),
    ) is not None


def create_registration_code(
    db: Session,
    organization_id: int,
    actor_user_id: int,
    expires_in_days: int | None,
) -> tuple[str, OrganizationRegistrationCode]:
    now = datetime.now(timezone.utc)
    raw_code = generate_secure_token()
    expires_at = (
        now + timedelta(days=expires_in_days)
        if expires_in_days is not None
        else None
    )

    try:
        db.execute(
            update(OrganizationRegistrationCode)
            .where(
                OrganizationRegistrationCode.organization_id
                == organization_id,
                OrganizationRegistrationCode.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        registration_code = OrganizationRegistrationCode(
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            code_hash=hash_token(raw_code),
            expires_at=expires_at,
        )
        db.add(registration_code)
        db.flush()
        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=actor_user_id,
                actor_organization_id=organization_id,
                action="ORGANIZATION_REGISTRATION_CODE_CREATE",
                resource_type="organization_registration_code",
                resource_id=registration_code.id,
            )
        )
        db.commit()
        db.refresh(registration_code)
        return raw_code, registration_code
    except Exception:
        db.rollback()
        raise


def revoke_registration_codes(
    db: Session,
    organization_id: int,
    actor_user_id: int,
) -> bool:
    now = datetime.now(timezone.utc)
    try:
        result = db.execute(
            update(OrganizationRegistrationCode)
            .where(
                OrganizationRegistrationCode.organization_id
                == organization_id,
                OrganizationRegistrationCode.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        if result.rowcount == 0:
            db.rollback()
            return False

        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=actor_user_id,
                actor_organization_id=organization_id,
                action="ORGANIZATION_REGISTRATION_CODE_REVOKE",
                resource_type="organization_registration_code",
            )
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def _find_existing_registration(
    db: Session,
    email: str,
    employee_id: str,
) -> bool:
    existing_email = db.scalar(
        select(User.id).where(func.lower(User.email) == email.lower())
    )
    if existing_email is not None:
        return True
    existing_employee_id = db.scalar(
        select(Employee.id).where(Employee.employee_id == employee_id)
    )
    return existing_employee_id is not None


def create_employee_registration(
    db: Session,
    *,
    organization_code: str,
    email: str,
    password: str,
    full_name: str,
    employee_id: str,
    branch_id: int,
    department_id: int,
    job_title: str,
) -> tuple[User, str] | None:
    now = datetime.now(timezone.utc)
    registration_code = _active_registration_code(
        db,
        organization_code,
        now,
    )
    if registration_code is None:
        raise LifecycleTransitionError("Invalid registration code")

    email = email.strip().lower()
    employee_id = employee_id.strip()
    full_name = full_name.strip()
    job_title = job_title.strip()

    branch = db.scalar(
        select(Branch)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Branch.id == branch_id,
            Branch.organization_id == registration_code.organization_id,
            Branch.is_active.is_(True),
            Region.organization_id == registration_code.organization_id,
            Region.is_active.is_(True),
        )
    )
    if branch is None:
        raise LifecycleTransitionError("Invalid registration information")

    department = db.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.branch_id == branch.id,
            Department.is_active.is_(True),
        )
    )
    if department is None:
        raise LifecycleTransitionError("Invalid registration information")

    password_hash = hash_password(password)
    if _find_existing_registration(db, email, employee_id):
        return None

    user = User(
        organization_id=registration_code.organization_id,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        is_active=False,
        lifecycle_managed=True,
        approval_status="pending",
    )
    db.add(user)
    try:
        db.flush()
        employee = Employee(
            organization_id=registration_code.organization_id,
            user_id=user.id,
            employee_id=employee_id,
            branch_id=branch.id,
            department_id=department.id,
            job_title=job_title,
            is_active=False,
        )
        db.add(employee)

        raw_token = _replace_verification_token(db, user, now)
        db.add(
            AuditLog(
                organization_id=registration_code.organization_id,
                user_id=user.id,
                actor_organization_id=registration_code.organization_id,
                action="EMPLOYEE_REGISTRATION_SUBMITTED",
                resource_type="user",
                resource_id=user.id,
            )
        )
        db.commit()
        db.refresh(user)
        return user, raw_token
    except IntegrityError:
        db.rollback()
        if _find_existing_registration(db, email, employee_id):
            return None
        raise
    except Exception:
        db.rollback()
        raise


def _replace_verification_token(
    db: Session,
    user: User,
    now: datetime,
) -> str:
    db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw_token = generate_secure_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now
            + timedelta(
                minutes=settings.email_verification_token_expire_minutes,
            ),
        )
    )
    db.flush()
    return raw_token


def resend_registration_verification(
    db: Session,
    email: str,
) -> tuple[User, str] | None:
    user = db.scalar(
        select(User)
        .where(func.lower(User.email) == email.strip().lower())
        .with_for_update()
    )
    if (
        user is None
        or not user.lifecycle_managed
        or user.approval_status != "pending"
        or user.email_verified_at is not None
    ):
        return None

    now = datetime.now(timezone.utc)
    try:
        raw_token = _replace_verification_token(db, user, now)
        db.commit()
        db.refresh(user)
        return user, raw_token
    except Exception:
        db.rollback()
        raise


def verify_registration_email(db: Session, raw_token: str) -> User:
    now = datetime.now(timezone.utc)
    token_record = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_token(raw_token),
            EmailVerificationToken.used_at.is_(None),
        )
    )
    if (
        token_record is None
        or ensure_utc(token_record.expires_at) <= now
    ):
        raise LifecycleTransitionError(
            "Invalid or expired email verification token"
        )

    user = db.scalar(
        select(User)
        .where(User.id == token_record.user_id)
        .with_for_update()
    )
    if (
        user is None
        or not user.lifecycle_managed
        or user.approval_status != "pending"
        or user.email_verified_at is not None
    ):
        raise LifecycleTransitionError(
            "Invalid or expired email verification token"
        )

    claim = db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.id == token_record.id,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > now,
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if claim.rowcount != 1:
        raise LifecycleTransitionError(
            "Invalid or expired email verification token"
        )

    user.email_verified_at = now
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            actor_organization_id=user.organization_id,
            action="USER_EMAIL_VERIFIED",
            resource_type="user",
            resource_id=user.id,
        )
    )
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def send_employee_verification_email(
    email_service: EmailService,
    user: User,
    raw_token: str,
) -> None:
    subject, body = build_employee_verification_email(
        raw_token=raw_token,
    )
    email_service.send(
        recipient=user.email,
        subject=subject,
        body=body,
    )
