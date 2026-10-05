from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
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
