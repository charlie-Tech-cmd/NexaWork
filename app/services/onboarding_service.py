import json
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_invitation import EmployeeInvitation
from app.models.employee_registration import EmployeeRegistrationRequest
from app.models.organization import Organization
from app.models.organization_registration_code import OrganizationRegistrationCode
from app.models.region import Region
from app.models.user import User


def _new_token() -> str:
    return secrets.token_urlsafe(24)


def _record_audit(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    action: str,
    resource_type: str,
    resource_id: int | None,
    details: dict[str, str] | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_organization_id=organization_id,
            user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details, sort_keys=True) if details else None,
        )
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def resolve_registration_organization(db: Session, registration_code: str) -> int:
    normalized_code = registration_code.strip().upper()
    code_record = db.scalar(
        select(OrganizationRegistrationCode).where(
            OrganizationRegistrationCode.code == normalized_code,
            OrganizationRegistrationCode.is_active.is_(True),
            OrganizationRegistrationCode.revoked_at.is_(None),
        )
    )
    if code_record is None:
        raise ValueError("Organization registration code is invalid")
    expiry = _as_utc(code_record.expires_at)
    if expiry is not None and datetime.now(timezone.utc) > expiry:
        code_record.is_active = False
        db.commit()
        raise ValueError("Organization registration code has expired")
    organization = db.scalar(
        select(Organization).where(
            Organization.id == code_record.organization_id,
            Organization.is_active.is_(True),
        )
    )
    if organization is None:
        raise ValueError("Organization registration code is invalid")
    return code_record.organization_id


def _generate_employee_number(db: Session, organization_id: int) -> str:
    prefix = f"NEXA-{organization_id}-"
    existing = db.scalar(
        select(Employee.id)
        .where(Employee.organization_id == organization_id)
        .order_by(Employee.id.desc())
    )
    next_number = (existing or 0) + 1
    return f"{prefix}{next_number:05d}"


def _ensure_branch_department(db: Session, organization_id: int, branch_id: int, department_id: int) -> None:
    branch = db.scalar(
        select(Branch)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Branch.id == branch_id,
            Branch.organization_id == organization_id,
            Region.organization_id == organization_id,
            Branch.is_active.is_(True),
            Region.is_active.is_(True),
        )
    )
    if branch is None:
        raise ValueError("Branch not found")

    department = db.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.branch_id == branch_id,
            Department.is_active.is_(True),
        )
    )
    if department is None:
        raise ValueError("Department not found")


def get_registration_structure(
    db: Session,
    registration_code: str,
) -> list[dict[str, object]]:
    organization_id = resolve_registration_organization(db, registration_code)
    rows = db.execute(
        select(Branch.id, Branch.name, Department.id, Department.name)
        .join(Region, Region.id == Branch.region_id)
        .join(
            Department,
            (Department.branch_id == Branch.id) & Department.is_active.is_(True),
        )
        .where(
            Branch.organization_id == organization_id,
            Region.organization_id == organization_id,
            Branch.is_active.is_(True),
            Region.is_active.is_(True),
        )
        .order_by(Branch.name, Department.name)
    ).all()

    branches: dict[int, dict[str, object]] = {}
    for branch_id, branch_name, department_id, department_name in rows:
        branch = branches.setdefault(
            branch_id,
            {"id": branch_id, "name": branch_name, "departments": []},
        )
        departments = branch["departments"]
        if isinstance(departments, list):
            departments.append({"id": department_id, "name": department_name})
    return list(branches.values())


def create_registration_code(
    db: Session,
    organization_id: int,
    created_by_user_id: int,
    expires_in_minutes: int | None = None,
) -> OrganizationRegistrationCode:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.is_active.is_(True),
        )
    )
    if organization is None:
        raise ValueError("Organization not found")

    record = _build_registration_code(
        db,
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
        expires_in_minutes=expires_in_minutes,
    )
    db.add(record)
    db.flush()
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=created_by_user_id,
        action="onboarding.registration_code.created",
        resource_type="organization_registration_code",
        resource_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return record


def _build_registration_code(
    db: Session,
    *,
    organization_id: int,
    created_by_user_id: int,
    expires_in_minutes: int | None,
) -> OrganizationRegistrationCode:
    code_value = _new_token().replace("-", "").upper()[:24]
    while db.scalar(
        select(OrganizationRegistrationCode.id).where(
            OrganizationRegistrationCode.code == code_value,
        )
    ) is not None:
        code_value = _new_token().replace("-", "").upper()[:24]

    expires_at = None
    if expires_in_minutes is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

    return OrganizationRegistrationCode(
        organization_id=organization_id,
        code=code_value,
        created_by_user_id=created_by_user_id,
        expires_at=expires_at,
    )


def list_registration_codes(db: Session, organization_id: int) -> list[OrganizationRegistrationCode]:
    codes = db.scalars(
        select(OrganizationRegistrationCode)
        .where(OrganizationRegistrationCode.organization_id == organization_id)
        .order_by(OrganizationRegistrationCode.created_at.desc())
    ).all()
    now = datetime.now(timezone.utc)
    expired_codes = []
    for code in codes:
        expiry = _as_utc(code.expires_at)
        if code.is_active and expiry is not None and now > expiry:
            code.is_active = False
            expired_codes.append(code)
    if expired_codes:
        db.commit()
    return codes


def revoke_registration_code(
    db: Session,
    *,
    organization_id: int,
    code_id: int,
    actor_user_id: int,
) -> OrganizationRegistrationCode:
    code_record = db.scalar(
        select(OrganizationRegistrationCode)
        .where(
            OrganizationRegistrationCode.id == code_id,
            OrganizationRegistrationCode.organization_id == organization_id,
        )
        .with_for_update()
    )
    if code_record is None:
        raise ValueError("Registration code not found")
    if not code_record.is_active or code_record.revoked_at is not None:
        raise ValueError("Registration code is no longer active")

    code_record.is_active = False
    code_record.revoked_at = datetime.now(timezone.utc)
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="onboarding.registration_code.revoked",
        resource_type="organization_registration_code",
        resource_id=code_record.id,
    )
    db.commit()
    db.refresh(code_record)
    return code_record


def rotate_registration_code(
    db: Session,
    *,
    organization_id: int,
    code_id: int,
    actor_user_id: int,
    expires_in_minutes: int | None = None,
) -> OrganizationRegistrationCode:
    old_code = db.scalar(
        select(OrganizationRegistrationCode)
        .where(
            OrganizationRegistrationCode.id == code_id,
            OrganizationRegistrationCode.organization_id == organization_id,
        )
        .with_for_update()
    )
    if old_code is None:
        raise ValueError("Registration code not found")
    if not old_code.is_active or old_code.revoked_at is not None:
        raise ValueError("Only active registration codes may be rotated")

    old_code.is_active = False
    old_code.revoked_at = datetime.now(timezone.utc)
    replacement = _build_registration_code(
        db,
        organization_id=organization_id,
        created_by_user_id=actor_user_id,
        expires_in_minutes=expires_in_minutes,
    )
    db.add(replacement)
    db.flush()
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="onboarding.registration_code.rotated",
        resource_type="organization_registration_code",
        resource_id=replacement.id,
        details={"replaced_code_id": str(old_code.id)},
    )
    db.commit()
    db.refresh(replacement)
    return replacement


def create_self_registration_request(
    db: Session,
    *,
    organization_id: int,
    full_name: str,
    email: str,
    password: str,
    job_title: str,
    branch_id: int,
    department_id: int,
    registration_code: str,
) -> EmployeeRegistrationRequest:
    existing = db.scalar(
        select(EmployeeRegistrationRequest).where(
            EmployeeRegistrationRequest.organization_id == organization_id,
            EmployeeRegistrationRequest.email == email.strip().lower(),
        )
    )
    if existing is not None:
        raise ValueError("A registration request already exists for this email")

    user_exists = db.scalar(
        select(User.id).where(User.email == email.strip().lower())
    )
    if user_exists is not None:
        raise ValueError("An account already exists for this email")

    _ensure_branch_department(db, organization_id, branch_id, department_id)

    code_record = db.scalar(
        select(OrganizationRegistrationCode).where(
            OrganizationRegistrationCode.code == registration_code.strip().upper(),
            OrganizationRegistrationCode.organization_id == organization_id,
        )
    )
    if code_record is None:
        raise ValueError("Organization registration code is invalid")
    if not code_record.is_active or code_record.revoked_at is not None:
        raise ValueError("Organization registration code is no longer valid")
    expiry = _as_utc(code_record.expires_at)
    if expiry is not None and datetime.now(timezone.utc) > expiry:
        code_record.is_active = False
        db.commit()
        raise ValueError("Organization registration code has expired")

    request = EmployeeRegistrationRequest(
        organization_id=organization_id,
        email=email.strip().lower(),
        full_name=full_name.strip(),
        branch_id=branch_id,
        department_id=department_id,
        job_title=job_title.strip(),
        registration_code_id=code_record.id,
        password_hash=hash_password(password),
        verification_token=_new_token(),
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        email_verification_status="unverified",
        approval_status="pending",
        account_status="active",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def verify_registration_email(db: Session, token: str) -> EmployeeRegistrationRequest:
    request = db.scalar(
        select(EmployeeRegistrationRequest).where(
            EmployeeRegistrationRequest.verification_token == token,
            EmployeeRegistrationRequest.email_verification_status != "verified",
            EmployeeRegistrationRequest.approval_status == "pending",
        )
    )
    if request is None:
        raise ValueError("Verification token is invalid")
    expiry = _as_utc(request.verification_expires_at)
    if expiry is not None and datetime.now(timezone.utc) > expiry:
        request.verification_token = None
        db.commit()
        raise ValueError("Verification token has expired")

    request.email_verification_status = "verified"
    request.verification_token = None
    request.verification_expires_at = None
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request


def resend_registration_verification(
    db: Session,
    *,
    registration_code: str,
    email: str,
) -> EmployeeRegistrationRequest | None:
    code_record = db.scalar(
        select(OrganizationRegistrationCode).where(
            OrganizationRegistrationCode.code == registration_code.strip().upper(),
        )
    )
    if code_record is None:
        return None
    organization = db.scalar(
        select(Organization).where(
            Organization.id == code_record.organization_id,
            Organization.is_active.is_(True),
        )
    )
    if organization is None:
        return None
    request = db.scalar(
        select(EmployeeRegistrationRequest)
        .where(
            EmployeeRegistrationRequest.organization_id == code_record.organization_id,
            EmployeeRegistrationRequest.registration_code_id == code_record.id,
            EmployeeRegistrationRequest.email == email.strip().lower(),
            EmployeeRegistrationRequest.email_verification_status == "unverified",
            EmployeeRegistrationRequest.approval_status == "pending",
        )
        .with_for_update()
    )
    if request is None:
        return None
    request.verification_token = _new_token()
    request.verification_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request


def list_registration_requests(
    db: Session,
    organization_id: int,
) -> list[dict[str, object]]:
    rows = db.execute(
        select(EmployeeRegistrationRequest, Employee.employee_id)
        .outerjoin(
            User,
            (User.organization_id == EmployeeRegistrationRequest.organization_id)
            & (User.email == EmployeeRegistrationRequest.email),
        )
        .outerjoin(
            Employee,
            (Employee.user_id == User.id)
            & (Employee.organization_id == EmployeeRegistrationRequest.organization_id),
        )
        .where(EmployeeRegistrationRequest.organization_id == organization_id)
        .order_by(EmployeeRegistrationRequest.created_at.desc())
    ).all()
    return [
        {
            "id": registration_request.id,
            "organization_id": registration_request.organization_id,
            "email": registration_request.email,
            "full_name": registration_request.full_name,
            "branch_id": registration_request.branch_id,
            "department_id": registration_request.department_id,
            "job_title": registration_request.job_title,
            "email_verification_status": registration_request.email_verification_status,
            "approval_status": registration_request.approval_status,
            "account_status": registration_request.account_status,
            "approval_reason": registration_request.approval_reason,
            "created_at": registration_request.created_at,
            "employee_id": employee_id,
        }
        for registration_request, employee_id in rows
    ]


def approve_registration_request(
    db: Session,
    *,
    organization_id: int,
    request_id: int,
    approved_by_user_id: int,
    reason: str | None = None,
) -> EmployeeRegistrationRequest:
    request = db.scalar(
        select(EmployeeRegistrationRequest).where(
            EmployeeRegistrationRequest.id == request_id,
            EmployeeRegistrationRequest.organization_id == organization_id,
        ).with_for_update()
    )
    if request is None:
        raise ValueError("Registration request not found")
    if request.approval_status != "pending":
        raise ValueError("Registration request is no longer pending")
    if request.email_verification_status != "verified":
        raise ValueError("Employee email must be verified before approval")
    if request.password_hash is None:
        raise ValueError("Registration request is missing its password credential")

    existing_user = db.scalar(select(User.id).where(User.email == request.email))
    if existing_user is not None:
        request.approval_status = "rejected"
        request.approval_reason = "Account already exists for this email"
        request.rejected_by_user_id = approved_by_user_id
        request.rejected_at = datetime.now(timezone.utc)
        request.account_status = "disabled"
        request.verification_token = None
        request.verification_expires_at = None
        request.password_hash = None
        _record_audit(
            db,
            organization_id=organization_id,
            actor_user_id=approved_by_user_id,
            action="onboarding.registration_request.rejected",
            resource_type="employee_registration_request",
            resource_id=request.id,
            details={"reason": request.approval_reason},
        )
        db.commit()
        raise ValueError("Account already exists for this email")

    user = User(
        organization_id=organization_id,
        email=request.email,
        password_hash=request.password_hash,
        full_name=request.full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    employee = Employee(
        organization_id=organization_id,
        user_id=user.id,
        employee_id=_generate_employee_number(db, organization_id),
        branch_id=request.branch_id,
        department_id=request.department_id,
        job_title=request.job_title,
        profile_picture=None,
        is_active=True,
        email_verification_status="verified",
        approval_status="approved",
        account_status="active",
    )
    db.add(employee)

    request.approval_status = "approved"
    request.approval_reason = reason
    request.approved_by_user_id = approved_by_user_id
    request.approved_at = datetime.now(timezone.utc)
    request.account_status = "active"
    request.email_verification_status = "verified"
    request.verification_token = None
    request.verification_expires_at = None
    request.password_hash = None
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=approved_by_user_id,
        action="onboarding.registration_request.approved",
        resource_type="employee_registration_request",
        resource_id=request.id,
        details={"reason": reason or ""},
    )
    db.commit()
    db.refresh(request)
    return request


def reject_registration_request(
    db: Session,
    *,
    organization_id: int,
    request_id: int,
    rejected_by_user_id: int,
    reason: str | None = None,
) -> EmployeeRegistrationRequest:
    request = db.scalar(
        select(EmployeeRegistrationRequest).where(
            EmployeeRegistrationRequest.id == request_id,
            EmployeeRegistrationRequest.organization_id == organization_id,
        ).with_for_update()
    )
    if request is None:
        raise ValueError("Registration request not found")
    if request.approval_status != "pending":
        raise ValueError("Registration request is no longer pending")

    request.approval_status = "rejected"
    request.approval_reason = reason or "Rejected by administrator"
    request.rejected_by_user_id = rejected_by_user_id
    request.rejected_at = datetime.now(timezone.utc)
    request.account_status = "disabled"
    request.verification_token = None
    request.verification_expires_at = None
    request.password_hash = None
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=rejected_by_user_id,
        action="onboarding.registration_request.rejected",
        resource_type="employee_registration_request",
        resource_id=request.id,
        details={"reason": request.approval_reason},
    )
    db.commit()
    db.refresh(request)
    return request


def create_employee_invitation(
    db: Session,
    *,
    organization_id: int,
    created_by_user_id: int,
    full_name: str,
    email: str,
    job_title: str,
    branch_id: int,
    department_id: int,
    expires_in_minutes: int = 1440,
) -> EmployeeInvitation:
    _ensure_branch_department(db, organization_id, branch_id, department_id)
    existing = db.scalar(
        select(EmployeeInvitation).where(
            EmployeeInvitation.organization_id == organization_id,
            EmployeeInvitation.email == email.strip().lower(),
            EmployeeInvitation.status == "pending",
        ).with_for_update()
    )
    if existing is not None:
        raise ValueError("An active invitation for this email already exists")
    existing_user = db.scalar(
        select(User.id).where(User.email == email.strip().lower())
    )
    if existing_user is not None:
        raise ValueError("An account already exists for this email")

    invitation = EmployeeInvitation(
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
        full_name=full_name.strip(),
        email=email.strip().lower(),
        job_title=job_title.strip(),
        branch_id=branch_id,
        department_id=department_id,
        invitation_token=_new_token(),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
    )
    db.add(invitation)
    db.flush()
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=created_by_user_id,
        action="onboarding.invitation.created",
        resource_type="employee_invitation",
        resource_id=invitation.id,
    )
    db.commit()
    db.refresh(invitation)
    return invitation


def list_employee_invitations(db: Session, organization_id: int) -> list[EmployeeInvitation]:
    invitations = db.scalars(
        select(EmployeeInvitation)
        .where(EmployeeInvitation.organization_id == organization_id)
        .order_by(EmployeeInvitation.created_at.desc())
    ).all()
    now = datetime.now(timezone.utc)
    expired_invitations = []
    for invitation in invitations:
        expiry = _as_utc(invitation.expires_at)
        if (
            invitation.status == "pending"
            and expiry is not None
            and now > expiry
        ):
            invitation.status = "expired"
            invitation.invitation_token = _new_token()
            expired_invitations.append(invitation)
    if expired_invitations:
        db.commit()
    return invitations


def list_employee_accounts(
    db: Session,
    organization_id: int,
) -> list[dict[str, object]]:
    rows = db.execute(
        select(Employee, User)
        .join(User, User.id == Employee.user_id)
        .where(Employee.organization_id == organization_id)
        .order_by(Employee.created_at.desc())
    ).all()
    return [
        {
            "id": employee.id,
            "organization_id": employee.organization_id,
            "employee_id": employee.employee_id,
            "email": user.email,
            "full_name": user.full_name,
            "branch_id": employee.branch_id,
            "department_id": employee.department_id,
            "job_title": employee.job_title,
            "email_verification_status": employee.email_verification_status,
            "approval_status": employee.approval_status,
            "account_status": employee.account_status,
            "approval_reason": employee.approval_reason,
            "account_status_reason": employee.account_status_reason,
            "created_at": employee.created_at,
        }
        for employee, user in rows
    ]


def resend_invitation(
    db: Session,
    invitation_id: int,
    organization_id: int,
    actor_user_id: int,
) -> EmployeeInvitation:
    invitation = db.scalar(
        select(EmployeeInvitation).where(
            EmployeeInvitation.id == invitation_id,
            EmployeeInvitation.organization_id == organization_id,
        ).with_for_update()
    )
    if invitation is None:
        raise ValueError("Invitation not found")
    if invitation.status != "pending":
        raise ValueError("Only pending invitations may be resent")
    invitation.invitation_token = _new_token()
    invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="onboarding.invitation.resent",
        resource_type="employee_invitation",
        resource_id=invitation.id,
    )
    db.commit()
    db.refresh(invitation)
    return invitation


def revoke_invitation(
    db: Session,
    invitation_id: int,
    organization_id: int,
    actor_user_id: int,
) -> EmployeeInvitation:
    invitation = db.scalar(
        select(EmployeeInvitation).where(
            EmployeeInvitation.id == invitation_id,
            EmployeeInvitation.organization_id == organization_id,
        ).with_for_update()
    )
    if invitation is None:
        raise ValueError("Invitation not found")
    if invitation.status != "pending":
        raise ValueError("Only pending invitations may be revoked")
    invitation.status = "revoked"
    invitation.revoked_at = datetime.now(timezone.utc)
    invitation.invitation_token = _new_token()
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="onboarding.invitation.revoked",
        resource_type="employee_invitation",
        resource_id=invitation.id,
    )
    db.commit()
    db.refresh(invitation)
    return invitation


def accept_invitation(
    db: Session,
    *,
    token: str,
    password: str,
) -> tuple[EmployeeInvitation, str]:
    invitation = db.scalar(
        select(EmployeeInvitation).where(
            EmployeeInvitation.invitation_token == token,
            EmployeeInvitation.status == "pending",
        ).with_for_update()
    )
    if invitation is None:
        raise ValueError("Invitation is invalid or no longer active")
    expiry = _as_utc(invitation.expires_at)
    if expiry is not None and datetime.now(timezone.utc) > expiry:
        invitation.status = "expired"
        invitation.invitation_token = _new_token()
        db.commit()
        raise ValueError("Invitation has expired")

    existing_user = db.scalar(
        select(User.id).where(User.email == invitation.email.lower())
    )
    if existing_user is not None:
        raise ValueError("An account already exists for this employee")

    user = User(
        organization_id=invitation.organization_id,
        email=invitation.email.lower(),
        password_hash=hash_password(password),
        full_name=invitation.full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    employee = Employee(
        organization_id=invitation.organization_id,
        user_id=user.id,
        employee_id=_generate_employee_number(db, invitation.organization_id),
        branch_id=invitation.branch_id,
        department_id=invitation.department_id,
        job_title=invitation.job_title,
        profile_picture=None,
        is_active=True,
        email_verification_status="verified",
        approval_status="approved",
        account_status="active",
    )
    db.add(employee)

    invitation.status = "accepted"
    invitation.invitation_token = _new_token()
    invitation.accepted_at = datetime.now(timezone.utc)
    employee_id = employee.employee_id
    db.commit()
    db.refresh(invitation)
    return invitation, employee_id


def disable_employee_account(
    db: Session,
    employee_id: int,
    organization_id: int,
    actor_user_id: int,
    reason: str | None = None,
) -> Employee:
    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.organization_id == organization_id,
        )
    )
    if employee is None:
        raise ValueError("Employee not found")
    if employee.account_status != "active":
        raise ValueError("Employee account is already disabled")
    user = db.scalar(select(User).where(User.id == employee.user_id))
    if user is not None:
        user.is_active = False
        user.token_version += 1
    employee.is_active = False
    employee.account_status = "disabled"
    employee.approval_status = "approved"
    employee.account_status_reason = reason
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="onboarding.employee.disabled",
        resource_type="employee",
        resource_id=employee.id,
        details={"reason": reason or ""},
    )
    db.commit()
    db.refresh(employee)
    return employee


def reenable_employee_account(
    db: Session,
    employee_id: int,
    organization_id: int,
    actor_user_id: int,
) -> Employee:
    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.organization_id == organization_id,
        )
    )
    if employee is None:
        raise ValueError("Employee not found")
    if employee.account_status != "disabled":
        raise ValueError("Employee account is already enabled")
    user = db.scalar(select(User).where(User.id == employee.user_id))
    if user is not None:
        user.is_active = True
    employee.is_active = True
    employee.account_status = "active"
    employee.account_status_reason = None
    _record_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="onboarding.employee.enabled",
        resource_type="employee",
        resource_id=employee.id,
    )
    db.commit()
    db.refresh(employee)
    return employee
