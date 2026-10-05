from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security.password import hash_password, verify_password
from app.models.user import User


def create_user(
    db: Session,
    organization_id: int,
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

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def deactivate_user(
    db: Session,
    user_id: int,
    organization_id: int,
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

    user.is_active = False

    db.commit()
    db.refresh(user)

    return user

def update_user(
    db: Session,
    user_id: int,
    organization_id: int,
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

    if full_name is not None:
        user.full_name = full_name

    if is_active is not None:
        user.is_active = is_active

    db.commit()
    db.refresh(user)

    return user
