import pytest
from sqlalchemy.exc import IntegrityError

from app.models.organization import Organization
from app.models.user import User


def create_organization(db_session):
    organization = Organization(
        name="Test Organization",
        slug="test-organization",
    )
    db_session.add(organization)
    db_session.flush()
    return organization


def test_normal_user_requires_organization(db_session):
    organization = create_organization(db_session)

    user = User(
        organization_id=organization.id,
        email="user@example.com",
        password_hash="hashed-password",
        full_name="Test User",
        is_super_admin=False,
    )

    db_session.add(user)
    db_session.commit()

    assert user.organization_id == organization.id
    assert user.is_super_admin is False


def test_super_admin_can_exist_without_organization(db_session):
    user = User(
        organization_id=None,
        email="superadmin@example.com",
        password_hash="hashed-password",
        full_name="Super Admin",
        is_super_admin=True,
    )

    db_session.add(user)
    db_session.commit()

    assert user.organization_id is None
    assert user.is_super_admin is True


def test_super_admin_cannot_have_organization(db_session):
    organization = create_organization(db_session)

    user = User(
        organization_id=organization.id,
        email="invalid-superadmin@example.com",
        password_hash="hashed-password",
        full_name="Invalid Super Admin",
        is_super_admin=True,
    )

    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_normal_user_cannot_exist_without_organization(db_session):
    user = User(
        organization_id=None,
        email="invalid-user@example.com",
        password_hash="hashed-password",
        full_name="Invalid User",
        is_super_admin=False,
    )

    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
