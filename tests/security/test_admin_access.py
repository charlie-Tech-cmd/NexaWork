import jwt
import pytest

from app.api.dependencies import get_current_admin
from app.core.config import settings
from app.core.security.jwt import create_access_token
from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.user import User


def create_admin_test_data(db_session):
    organization = Organization(
        name="Admin Test Organization",
        slug="admin-test-organization",
        is_active=True,
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="admin.access@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Admin Access User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    return organization, user


def test_get_current_admin_allows_admin_token(db_session):
    _, user = create_admin_test_data(db_session)

    token = create_access_token(str(user.id), auth_type="admin")

    result = get_current_admin(
        token=token,
        db=db_session,
    )

    assert result.id == user.id


def test_get_current_admin_rejects_employee_token(db_session):
    _, user = create_admin_test_data(db_session)

    token = create_access_token(str(user.id), auth_type="employee")

    with pytest.raises(Exception) as exc_info:
        get_current_admin(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin authentication required"


def test_get_current_admin_rejects_inactive_organization(db_session):
    organization, user = create_admin_test_data(db_session)

    organization.is_active = False
    db_session.commit()

    token = create_access_token(str(user.id), auth_type="admin")

    with pytest.raises(Exception) as exc_info:
        get_current_admin(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == (
        "Organization is inactive or unavailable"
    )


def test_get_current_admin_rejects_inactive_user(db_session):
    _, user = create_admin_test_data(db_session)

    user.is_active = False
    db_session.commit()

    token = create_access_token(str(user.id), auth_type="admin")

    with pytest.raises(Exception) as exc_info:
        get_current_admin(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not found"
