from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security.account_lifecycle import can_activate_account
from app.core.security.password import hash_password, verify_password
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.account_lifecycle_service import LifecycleTransitionError


def create_user(
    db: Session,
    organization_id: int,
    actor_user_id: int,
    email: str,
    password: str,
    full_name: str,
) -> User:
    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        raise ValueError("Email already registered")

    new_user = User(
        organization_id=organization_id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
    )

    try:
        db.add(new_user)
        db.flush()

        audit_log = AuditLog(
            organization_id=organization_id,
            user_id=actor_user_id,
            actor_organization_id=organization_id,
            action="USER_CREATE",
            resource_type="user",
            resource_id=new_user.id,
        )
        db.add(audit_log)

        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception:
        db.rollback()
        raise


def deactivate_user(
    db: Session,
    user_id: int,
    organization_id: int,
    actor_user_id: int,
    password: str,
    current_user_password_hash: str,
) -> User:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )

    if user is None:
        raise ValueError("User not found")

    if not verify_password(password, current_user_password_hash):
        raise ValueError("Invalid password")

    try:
        if user.is_active:
            user.token_version += 1
        user.is_active = False
        audit_log = AuditLog(
            organization_id=organization_id,
            user_id=actor_user_id,
            actor_organization_id=organization_id,
            action="USER_DEACTIVATE",
            resource_type="user",
            resource_id=user.id,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def list_users(
    db: Session,
    organization_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    users = db.scalars(
        select(User)
        .where(
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
        .order_by(User.id)
        .offset(offset)
        .limit(limit)
    ).all()

    return users


def get_user(
    db: Session,
    user_id: int,
    organization_id: int,
) -> User:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise ValueError("User not found")

    return user


def update_user(
    db: Session,
    user_id: int,
    organization_id: int,
    actor_user_id: int,
    email: str | None,
    full_name: str | None,
    is_active: bool | None,
) -> User:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )

    if user is None:
        raise ValueError("User not found")

    email_changed = email is not None and email != user.email
    if is_active is True and user.lifecycle_managed and email_changed:
        raise LifecycleTransitionError(
            "Email changes require reverification before activation"
        )
    if is_active is True and not can_activate_account(user):
        raise LifecycleTransitionError(
            "Email verification and approval are required before activation"
        )

    if email is not None:
        existing_user = db.scalar(
            select(User).where(
                User.email == email,
                User.id != user_id,
            )
        )

        if existing_user is not None:
            raise ValueError("Email already registered")

        user.email = email
        if email_changed and user.lifecycle_managed:
            user.email_verified_at = None
            user.is_active = False
            user.token_version += 1

    if full_name is not None:
        user.full_name = full_name

    if is_active is not None and user.is_active != is_active:
        user.is_active = is_active
        user.token_version += 1

    try:
        audit_log = AuditLog(
            organization_id=organization_id,
            user_id=actor_user_id,
            actor_organization_id=organization_id,
            action="USER_UPDATE",
            resource_type="user",
            resource_id=user.id,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
