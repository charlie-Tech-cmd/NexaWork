from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings


def create_access_token(
    subject: str,
    auth_type: str | None = None,
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "exp": expires_at,
    }

    if auth_type is not None:
        payload["auth_type"] = auth_type

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise ValueError("Invalid or expired token") from exc