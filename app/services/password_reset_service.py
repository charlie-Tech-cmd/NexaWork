from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security.password import hash_password
from app.core.security.reset_token import (
    generate_reset_token,
    hash_reset_token,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def create_password_reset_token(
    db: Session,
    user: User,
) -> tuple[str, PasswordResetToken]:
    now = datetime.now(timezone.utc)

    active_tokens = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .all()
    )

    for token_record in active_tokens:
        token_record.used_at = now

    raw_token = generate_reset_token()

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=now
        + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        ),
    )

    db.add(reset_token)
    db.flush()

    return raw_token, reset_token


def reset_password(
    db: Session,
    raw_token: str,
    new_password: str,
) -> None:
    now = datetime.now(timezone.utc)
    token_hash = hash_reset_token(raw_token)

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )

    if reset_token is None:
        raise ValueError("Invalid or expired password reset token")

    if ensure_utc(reset_token.expires_at) <= now:
        raise ValueError("Invalid or expired password reset token")

    user = db.get(User, reset_token.user_id)

    if user is None:
        raise ValueError("Invalid or expired password reset token")

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    reset_token.used_at = now

    db.flush()
