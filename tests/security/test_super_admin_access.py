import pytest

from app.api.dependencies import get_current_super_admin
from app.core.security.jwt import create_access_token
from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.user import User


def create_super_admin_test_data(db_session):
    user = User(
        organization_id=None,
        email="superadmin.access@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Super Admin",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(user)
    db_session.commit()

    return user


def create_organization_user(db_session):
    organization = Organization(
        name="Super Admin Test Organization",
        slug="super-admin-test-organization",
        is_active=True,
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="organization.user@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization User",
        is_active=True,
        is_super_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    return organization, user


def test_get_current_super_admin_allows_super_admin_token(db_session):
    user = create_super_admin_test_data(db_session)

    token = create_access_token(
        str(user.id),
        auth_type="super_admin",
    )

    result = get_current_super_admin(
        token=token,
        db=db_session,
    )

    assert result.id == user.id


def test_get_current_super_admin_rejects_admin_token(db_session):
    user = create_super_admin_test_data(db_session)

    token = create_access_token(
        str(user.id),
        auth_type="admin",
    )

    with pytest.raises(Exception) as exc_info:
        get_current_super_admin(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Super Admin authentication required"


def test_get_current_super_admin_rejects_normal_user(db_session):
    _, user = create_organization_user(db_session)

    token = create_access_token(
        str(user.id),
        auth_type="super_admin",
    )

    with pytest.raises(Exception) as exc_info:
        get_current_super_admin(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Super Admin access required"


def test_get_current_super_admin_rejects_inactive_super_admin(db_session):
    user = create_super_admin_test_data(db_session)

    user.is_active = False
    db_session.commit()

    token = create_access_token(
        str(user.id),
        auth_type="super_admin",
    )

    with pytest.raises(Exception) as exc_info:
        get_current_super_admin(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Super Admin access required"