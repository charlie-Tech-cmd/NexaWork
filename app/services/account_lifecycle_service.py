from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security.account_lifecycle import can_activate_account
from app.models.audit_log import AuditLog
from app.models.user import User


RegistrationDecision = Literal["approved", "rejected"]


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

    user.approval_status = decision
    user.is_active = decision == "approved" and can_activate_account(user)
    user.token_version += 1
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
        )
    )

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
