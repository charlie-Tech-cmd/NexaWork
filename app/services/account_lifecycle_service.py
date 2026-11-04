from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.security.account_lifecycle import can_activate_account
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.department import Department
from app.models.email_verification_token import EmailVerificationToken
from app.models.employee import Employee
from app.models.region import Region
from app.models.user import User


RegistrationDecision = Literal["approved", "rejected"]


def list_pending_registrations(
    db: Session,
    organization_id: int,
    limit: int,
    offset: int,
) -> dict[str, object]:
    filters = (
        User.organization_id == organization_id,
        User.lifecycle_managed.is_(True),
        User.approval_status == "pending",
        Employee.organization_id == organization_id,
    )
    total = db.scalar(
        select(func.count(User.id))
        .join(Employee, Employee.user_id == User.id)
        .where(*filters)
    ) or 0
    rows = db.execute(
        select(User, Employee, Branch, Department)
        .join(Employee, Employee.user_id == User.id)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Department, Department.id == Employee.department_id)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "employee_id": employee.employee_id,
            "branch_id": branch.id,
            "branch_name": branch.name,
            "department_id": department.id,
            "department_name": department.name,
            "job_title": employee.job_title,
            "submitted_at": user.created_at,
            "email_verified": user.email_verified_at is not None,
        }
        for user, employee, branch, department in rows
    ]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def list_rejected_registrations(
    db: Session,
    organization_id: int,
    limit: int,
    offset: int,
) -> dict[str, object]:
    decision_actor = aliased(User)
    filters = (
        User.organization_id == organization_id,
        User.lifecycle_managed.is_(True),
        User.approval_status == "rejected",
        Employee.organization_id == organization_id,
        AuditLog.organization_id == organization_id,
        AuditLog.resource_type == "user",
        AuditLog.resource_id == User.id,
        AuditLog.action == "EMPLOYEE_REGISTRATION_REJECTED",
        AuditLog.actor_organization_id == organization_id,
    )
    query = (
        select(User, Employee, Branch, Department, AuditLog, decision_actor)
        .join(Employee, Employee.user_id == User.id)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Department, Department.id == Employee.department_id)
        .join(AuditLog, AuditLog.resource_id == User.id)
        .join(decision_actor, decision_actor.id == AuditLog.user_id)
        .where(*filters)
    )
    total = db.scalar(
        select(func.count(AuditLog.id))
        .join(User, User.id == AuditLog.resource_id)
        .join(Employee, Employee.user_id == User.id)
        .where(*filters)
    ) or 0
    rows = db.execute(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "employee_id": employee.employee_id,
            "branch_id": branch.id,
            "branch_name": branch.name,
            "department_id": department.id,
            "department_name": department.name,
            "job_title": employee.job_title,
            "submitted_at": user.created_at,
            "email_verified": user.email_verified_at is not None,
            "rejected_at": audit.created_at,
            "rejected_by": actor.full_name,
            "rejection_reason": audit.details,
        }
        for user, employee, branch, department, audit, actor in rows
    ]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


class LifecycleTransitionError(ValueError):
    pass


def mark_email_verified(
    db: Session,
    user_id: int,
    organization_id: int,
) -> User:
    user = db.scalar(
        select(User)
        .where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
        .with_for_update()
    )
    if user is None:
        raise LifecycleTransitionError("User not found")
    if not user.lifecycle_managed:
        raise LifecycleTransitionError("User lifecycle is not managed")
    if user.approval_status == "rejected":
        raise LifecycleTransitionError("Rejected registration cannot be verified")
    if user.email_verified_at is not None:
        raise LifecycleTransitionError("Email is already verified")

    user.email_verified_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user.id,
            actor_organization_id=organization_id,
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


def decide_registration(
    db: Session,
    user_id: int,
    organization_id: int,
    actor_user_id: int,
    decision: RegistrationDecision,
    rejection_reason: str | None = None,
) -> User:
    if decision not in ("approved", "rejected"):
        raise LifecycleTransitionError("Invalid registration decision")

    user = db.scalar(
        select(User)
        .where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
        .with_for_update()
    )
    if user is None:
        raise LifecycleTransitionError("User not found")
    if not user.lifecycle_managed:
        raise LifecycleTransitionError("User lifecycle is not managed")
    if user.approval_status != "pending":
        raise LifecycleTransitionError("Registration is not pending")
    if actor_user_id == user_id:
        raise LifecycleTransitionError("Users cannot approve their own registration")
    if decision == "approved" and user.email_verified_at is None:
        raise LifecycleTransitionError("Email verification is required before approval")

    actor = db.scalar(
        select(User).where(
            User.id == actor_user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
    )
    if actor is None:
        raise LifecycleTransitionError("Approver not found in organization")

    employee = db.scalar(
        select(Employee)
        .where(
            Employee.user_id == user.id,
            Employee.organization_id == organization_id,
        )
        .with_for_update()
    )
    if decision == "approved" and employee is not None:
        active_placement = db.scalar(
            select(Employee.id)
            .join(Branch, Branch.id == Employee.branch_id)
            .join(Region, Region.id == Branch.region_id)
            .join(
                Department,
                Department.id == Employee.department_id,
            )
            .where(
                Employee.id == employee.id,
                Employee.organization_id == organization_id,
                Branch.organization_id == organization_id,
                Branch.is_active.is_(True),
                Region.organization_id == organization_id,
                Region.is_active.is_(True),
                Department.branch_id == Branch.id,
                Department.is_active.is_(True),
            )
        )
        if active_placement is None:
            raise LifecycleTransitionError(
                "Employee placement is inactive or unavailable"
            )
        employee.is_active = True
    elif employee is not None:
        employee.is_active = False

    user.approval_status = decision
    user.is_active = decision == "approved" and can_activate_account(user)
    user.token_version += 1
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None),
    ).update(
        {EmailVerificationToken.used_at: datetime.now(timezone.utc)},
        synchronize_session="fetch",
    )
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=actor.id,
            actor_organization_id=organization_id,
            action=(
                "EMPLOYEE_REGISTRATION_APPROVED"
                if decision == "approved"
                else "EMPLOYEE_REGISTRATION_REJECTED"
            ),
            resource_type="user",
            resource_id=user.id,
            details=(
                rejection_reason
                if decision == "rejected"
                else None
            ),
        )
    )

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
