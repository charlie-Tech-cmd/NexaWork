import pytest
from datetime import datetime, timedelta, timezone

from app.core.security.password import verify_password
from app.models.organization import Organization
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.password_reset_service import (
    create_password_reset_token,
    reset_password,
)


def create_test_user(db_session):
    organization = Organization(
        name="Password Reset Organization",
        slug="password-reset-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="reset@example.com",
        password_hash="test-password-hash",
        full_name="Reset User",
    )
    db_session.add(user)
    db_session.flush()

    return user


def test_create_password_reset_token_stores_hash_not_raw_token(db_session):
    user = create_test_user(db_session)

    raw_token, reset_token = create_password_reset_token(
        db_session,
        user,
    )

    assert raw_token
    assert reset_token.user_id == user.id
    assert reset_token.token_hash != raw_token
    assert len(reset_token.token_hash) == 64
    assert reset_token.used_at is None
    assert reset_token.expires_at > datetime.now(timezone.utc)


def test_create_password_reset_token_invalidates_previous_token(db_session):
    user = create_test_user(db_session)

    first_raw_token, first_record = create_password_reset_token(
        db_session,
        user,
    )

    second_raw_token, second_record = create_password_reset_token(
        db_session,
        user,
    )

    assert first_raw_token != second_raw_token
    assert first_record.used_at is not None
    assert second_record.used_at is None


def test_create_password_reset_token_creates_new_record(db_session):
    user = create_test_user(db_session)

    _, reset_token = create_password_reset_token(
        db_session,
        user,
    )

    stored_record = db_session.get(
        PasswordResetToken,
        reset_token.id,
    )

    assert stored_record is not None
    assert stored_record.user_id == user.id


def test_reset_password_updates_password_and_revokes_tokens(db_session):
    user = create_test_user(db_session)

    raw_token, reset_token = create_password_reset_token(
        db_session,
        user,
    )

    original_token_version = user.token_version

    reset_password(
        db_session,
        raw_token,
        "NewSecurePassword123!",
    )

    assert verify_password(
        "NewSecurePassword123!",
        user.password_hash,
    )

    assert not verify_password(
        "test-password",
        user.password_hash,
    )

    assert user.token_version == original_token_version + 1
    assert reset_token.used_at is not None


def test_reset_password_rejects_used_token(db_session):
    user = create_test_user(db_session)

    raw_token, _ = create_password_reset_token(
        db_session,
        user,
    )

    reset_password(
        db_session,
        raw_token,
        "NewSecurePassword123!",
    )

    with pytest.raises(ValueError, match="Invalid or expired"):
        reset_password(
            db_session,
            raw_token,
            "AnotherPassword123!",
        )


def test_reset_password_rejects_expired_token(db_session):
    user = create_test_user(db_session)

    raw_token, reset_token = create_password_reset_token(
        db_session,
        user,
    )

    reset_token.expires_at = datetime.now(timezone.utc) - timedelta(
        minutes=1
    )
    db_session.flush()

    with pytest.raises(ValueError, match="Invalid or expired"):
        reset_password(
            db_session,
            raw_token,
            "NewSecurePassword123!",
        )
