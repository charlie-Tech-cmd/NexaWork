import pytest
from argon2 import PasswordHasher
from sqlalchemy import select

from app.models.user import User
from app.scripts.create_super_admin import create_super_admin


password_hasher = PasswordHasher()


def test_create_super_admin_creates_platform_user(db_session):
    user = create_super_admin(
        db_session,
        email="owner@nexawork.com",
        full_name="NexaWork Owner",
        password="StrongPassword123!",
    )

    assert user.id is not None
    assert user.email == "owner@nexawork.com"
    assert user.full_name == "NexaWork Owner"
    assert user.is_active is True
    assert user.is_super_admin is True
    assert user.organization_id is None
    assert password_hasher.verify(
        user.password_hash,
        "StrongPassword123!",
    )


def test_create_super_admin_normalizes_email_and_name(db_session):
    user = create_super_admin(
        db_session,
        email="  OWNER@NEXAWORK.COM ",
        full_name="  NexaWork Owner  ",
        password="StrongPassword123!",
    )

    assert user.email == "owner@nexawork.com"
    assert user.full_name == "NexaWork Owner"


def test_create_super_admin_rejects_duplicate_email(db_session):
    create_super_admin(
        db_session,
        email="owner@nexawork.com",
        full_name="First Owner",
        password="StrongPassword123!",
    )

    with pytest.raises(
        ValueError,
        match="A user with this email already exists",
    ):
        create_super_admin(
            db_session,
            email="OWNER@NEXAWORK.COM",
            full_name="Second Owner",
            password="AnotherPassword123!",
        )


def test_create_super_admin_rejects_missing_email(db_session):
    with pytest.raises(ValueError, match="Email is required"):
        create_super_admin(
            db_session,
            email="",
            full_name="NexaWork Owner",
            password="StrongPassword123!",
        )


def test_create_super_admin_rejects_missing_name(db_session):
    with pytest.raises(ValueError, match="Full name is required"):
        create_super_admin(
            db_session,
            email="owner@nexawork.com",
            full_name="",
            password="StrongPassword123!",
        )


def test_create_super_admin_rejects_missing_password(db_session):
    with pytest.raises(ValueError, match="Password is required"):
        create_super_admin(
            db_session,
            email="owner@nexawork.com",
            full_name="NexaWork Owner",
            password="",
        )


def test_created_super_admin_is_persisted_as_platform_user(db_session):
    create_super_admin(
        db_session,
        email="owner@nexawork.com",
        full_name="NexaWork Owner",
        password="StrongPassword123!",
    )

    user = db_session.scalar(
        select(User).where(User.email == "owner@nexawork.com")
    )

    assert user is not None
    assert user.is_super_admin is True
    assert user.organization_id is None
    assert user.is_active is True
