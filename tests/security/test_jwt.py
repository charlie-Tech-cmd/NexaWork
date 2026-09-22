from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security.jwt import (
    create_access_token,
    decode_access_token,
)


def test_create_access_token_preserves_subject():
    token = create_access_token("123")

    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert "exp" in payload


def test_decode_access_token_rejects_expired_token():
    expired_token = jwt.encode(
        {
            "sub": "123",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_wrong_secret():
    token = jwt.encode(
        {
            "sub": "123",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        "wrong-secret",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(token)


def test_decode_access_token_rejects_malformed_token():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token("not-a-valid-jwt")