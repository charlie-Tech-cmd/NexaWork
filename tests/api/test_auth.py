from datetime import datetime, timedelta, timezone

import pytest
import redis

import jwt

from app.core.rate_limit import RateLimitUnavailable, is_login_allowed
from app.core.config import settings
from app.core.security.password import hash_password, verify_password
from app.core.security.reset_token import hash_reset_token
from app.core.redis import redis_client

from tests.helpers import create_password_reset_test_user
from app.models.password_reset_token import PasswordResetToken
from app.models.organization import Organization
from app.models.user import User
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.region import Region

from unittest.mock import patch


def test_login_returns_access_token(client, db_session):
    organization = Organization(
        name="Test Organization",
        slug="test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="auth.test@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Auth Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "auth.test@example.com",
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful"
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert "access_token" in data
    assert data["access_token"]

def test_auth_me_returns_authenticated_user(client, db_session):
    organization = Organization(
        name="Test Organization",
        slug="test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="me.test@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Me Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "me.test@example.com",
                "password": "SecurePassword123!",
            },
        )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "me.test@example.com",
        "full_name": "Me Test User",
        "is_active": True,
    }

def test_auth_me_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired token",
    }

def test_auth_me_rejects_inactive_user_token(client, db_session):
    organization = Organization(
        name="Inactive User Organization",
        slug="inactive-user-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.test@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive.test@example.com",
                "password": "SecurePassword123!",
            },
        )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    user.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "User not found",
    }


def test_auth_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Not authenticated",
    }


def test_auth_me_rejects_expired_token(client):
    expired_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired token",
    }


def test_auth_me_rejects_token_for_nonexistent_user(client):
    token = jwt.encode(
        {
            "sub": "999999",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "User not found",
    }


def test_auth_me_rejects_token_with_wrong_secret(client):
    token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        "wrong-secret-that-is-long-enough-for-hs256",
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired token",
    }

def test_admin_login_returns_admin_token(client, db_session):
    organization = Organization(
        name="Admin Login Organization",
        slug="admin-login-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="ADMIN_ACCESS",
        description="Access administrative portal",
        is_active=True,
    )

    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Organization Admin",
        description="Organization administrator",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="admin.login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Admin Login User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=permission.id,
        )
    )
    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=role.id,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Admin login successful"
    assert data["id"] == user.id
    assert data["access_token"]

    payload = jwt.decode(
        data["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == str(user.id)
    assert payload["auth_type"] == "admin"


def test_admin_login_rejects_user_without_admin_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Non Admin Organization",
        slug="non-admin-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee.admin.login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Regular User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Admin access required",
    }


def test_super_admin_login_returns_super_admin_token(
    client,
    db_session,
):
    user = User(
        organization_id=None,
        email="super.admin.login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Super Admin Login User",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Super Admin login successful"
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert data["full_name"] == user.full_name
    assert data["access_token"]

    payload = jwt.decode(
        data["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == str(user.id)
    assert payload["auth_type"] == "super_admin"


def test_super_admin_login_rejects_wrong_password(
    client,
    db_session,
):
    user = User(
        organization_id=None,
        email="super.admin.wrong.password@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Super Admin Wrong Password",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": user.email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
    }


def test_super_admin_login_rejects_normal_user(
    client,
    db_session,
):
    organization = Organization(
        name="Super Admin Normal User Organization",
        slug="super-admin-normal-user-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="normal.super.admin.login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Normal Organization User",
        is_active=True,
        is_super_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
    }


def test_super_admin_login_rejects_organization_admin(
    client,
    db_session,
):
    organization = Organization(
        name="Super Admin Organization Admin",
        slug="super-admin-organization-admin",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="ADMIN_ACCESS",
        description="Access administrative portal",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Organization Admin",
        description="Organization administrator",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="organization.admin.super.login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Admin",
        is_active=True,
        is_super_admin=False,
    )
    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=permission.id,
        )
    )
    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=role.id,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
    }


def test_super_admin_login_rejects_inactive_super_admin(
    client,
    db_session,
):
    user = User(
        organization_id=None,
        email="inactive.super.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Super Admin",
        is_active=False,
        is_super_admin=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
    }


def test_super_admin_login_rejects_rate_limited_request(client):
    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=False,
    ):
        response = client.post(
            "/api/v1/auth/super-admin/login",
            json={
                "email": "super.admin@example.com",
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many login attempts. Please try again later."
    )

def test_login_rejects_rate_limited_request(client):
    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=False,
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "blocked@example.com",
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many login attempts. Please try again later."
    )


def test_login_rejects_ip_rate_limited_request(client):
    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        with patch(
            "app.api.routes.auth.is_login_ip_allowed",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "ip-blocked@example.com",
                    "password": "SecurePassword123!",
                },
            )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many login attempts. Please try again later."
    )


def test_employee_login_rejects_rate_limited_request(client):
    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=False,
    ):
        response = client.post(
            "/api/v1/auth/employee/login",
            json={
                "employee_id": "EMP001",
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many login attempts. Please try again later."
    )

def test_admin_login_rejects_rate_limited_request(client):
    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=False,
    ):
        response = client.post(
            "/api/v1/auth/admin/login",
            json={
                "email": "admin@example.com",
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many login attempts. Please try again later."
    )


@pytest.mark.parametrize(
    ("path", "payload", "patch_target"),
    [
        (
            "/api/v1/auth/login",
            {
                "email": "outage@example.com",
                "password": "SecurePassword123!",
            },
            "is_login_allowed",
        ),
        (
            "/api/v1/auth/employee/login",
            {
                "employee_id": "EMP001",
                "password": "SecurePassword123!",
            },
            "is_login_allowed",
        ),
        (
            "/api/v1/auth/admin/login",
            {
                "email": "admin-outage@example.com",
                "password": "SecurePassword123!",
            },
            "is_login_allowed",
        ),
        (
            "/api/v1/auth/super-admin/login",
            {
                "email": "super-admin-outage@example.com",
                "password": "SecurePassword123!",
            },
            "is_login_allowed",
        ),
        (
            "/api/v1/auth/forgot-password",
            {"email": "recovery-outage@example.com"},
            "is_password_recovery_allowed",
        ),
    ],
)

def test_auth_rate_limit_redis_failure_returns_503(
    client,
    path,
    payload,
    patch_target,
):
    with patch(
        f"app.api.routes.auth.{patch_target}",
        side_effect=RateLimitUnavailable(),
    ):
        response = client.post(path, json=payload)

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Authentication is temporarily unavailable. "
            "Please try again later."
        ),
    }


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/v1/auth/login",
            {"email": "ip-outage@example.com", "password": "SecurePassword123!"},
        ),
        (
            "/api/v1/auth/employee/login",
            {"employee_id": "EMP-IP-001", "password": "SecurePassword123!"},
        ),
        (
            "/api/v1/auth/admin/login",
            {"email": "admin-ip-outage@example.com", "password": "SecurePassword123!"},
        ),
        (
            "/api/v1/auth/super-admin/login",
            {"email": "super-admin-ip-outage@example.com", "password": "SecurePassword123!"},
        ),
    ],
)
def test_login_ip_rate_limit_redis_failure_returns_503(client, path, payload):
    with (
        patch(
            "app.api.routes.auth.is_login_allowed",
            return_value=True,
        ),
        patch(
            "app.api.routes.auth.is_login_ip_allowed",
            side_effect=RateLimitUnavailable(),
        ),
    ):
        response = client.post(path, json=payload)

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Authentication is temporarily unavailable. "
            "Please try again later."
        ),
    }


def test_rate_limit_wraps_redis_error():
    with patch(
        "app.core.rate_limit.check_rate_limit",
        side_effect=redis.exceptions.RedisError("Redis unavailable"),
    ):
        with pytest.raises(RateLimitUnavailable):
            is_login_allowed("rate-limit-test")


def test_login_rejects_inactive_organization(client, db_session):
    organization = Organization(
        name="Inactive Login Organization",
        slug="inactive-login-organization",
        is_active=False,
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive-org-login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization is inactive or unavailable",
    }


def test_employee_login_rejects_inactive_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Employee Organization",
        slug="inactive-employee-organization",
        is_active=False,
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Employee Region",
        slug="inactive-employee-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Employee Branch",
        slug="inactive-employee-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Employee Department",
        slug="inactive-employee-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive-org-employee@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Organization Employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-INACTIVE-ORG",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        response = client.post(
            "/api/v1/auth/employee/login",
            json={
                "employee_id": employee.employee_id,
                "password": "SecurePassword123!",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization is inactive or unavailable",
    }


def test_auth_me_rejects_token_after_organization_deactivation(
    client,
    db_session,
):
    organization = Organization(
        name="Organization Deactivation Test",
        slug="organization-deactivation-test",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="organization-deactivation@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Deactivation User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "SecurePassword123!",
            },
        )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    organization.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization is inactive or unavailable",
    }


def test_auth_me_rejects_token_after_token_version_changes(
    client,
    db_session,
):
    organization = Organization(
        name="Token Revocation Organization",
        slug="token-revocation-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="token.revocation@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Token Revocation User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "SecurePassword123!",
            },
        )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    valid_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert valid_response.status_code == 200

    user.token_version += 1
    db_session.commit()

    revoked_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert revoked_response.status_code == 401
    assert revoked_response.json() == {
        "detail": "Invalid or expired token",
    }


def test_forgot_password_returns_generic_response_for_existing_user(
    client,
    db_session,
):
    organization = Organization(
        name="Forgot Password Organization",
        slug="forgot-password-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="forgot@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Forgot Password User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "forgot@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "If an account exists with that email, a password reset link has been sent.",
    }


def test_forgot_password_returns_same_response_for_unknown_email(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "does-not-exist@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "If an account exists with that email, a password reset link has been sent.",
    }


def test_reset_password_updates_password(client, db_session):
    organization = Organization(
        name="Reset Password API Organization",
        slug="reset-password-api-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="reset-api@example.com",
        password_hash=hash_password("OldPassword123!"),
        full_name="Reset API User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    raw_token = "test-reset-token"

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password reset successful",
    }

    db_session.refresh(user)
    db_session.refresh(reset_token)

    assert verify_password(
        "NewPassword123!",
        user.password_hash,
    )
    assert not verify_password(
        "OldPassword123!",
        user.password_hash,
    )
    assert user.token_version == 1
    assert reset_token.used_at is not None


def test_reset_password_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "invalid-reset-token",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid or expired password reset token",
    }


def test_reset_password_rejects_expired_token(client, db_session):
    organization = Organization(
        name="Expired Reset API Organization",
        slug="expired-reset-api-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="expired-reset-api@example.com",
        password_hash=hash_password("OldPassword123!"),
        full_name="Expired Reset API User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    raw_token = "expired-reset-token"

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid or expired password reset token",
    }


def test_reset_password_rejects_used_token(client, db_session):
    organization = Organization(
        name="Used Reset API Organization",
        slug="used-reset-api-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="used-reset-api@example.com",
        password_hash=hash_password("OldPassword123!"),
        full_name="Used Reset API User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    raw_token = "used-reset-token"

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used_at=datetime.now(timezone.utc),
    )
    db_session.add(reset_token)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid or expired password reset token",
    }


def test_reset_password_revokes_existing_access_token(client, db_session):
    organization = Organization(
        name="Reset Revocation Organization",
        slug="reset-revocation-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="reset-revocation@example.com",
        password_hash=hash_password("OldPassword123!"),
        full_name="Reset Revocation User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "reset-revocation@example.com",
            "password": "OldPassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert me_response.status_code == 200

    raw_token = "reset-revocation-token"

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(reset_token)
    db_session.commit()

    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewPassword123!",
        },
    )

    assert reset_response.status_code == 200

    revoked_response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert revoked_response.status_code == 401
    assert revoked_response.json() == {
        "detail": "Invalid or expired token",
    }


def test_forgot_password_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_max_attempts", 1)

    email = "rate-limit-reset-unique-20261002@example.com"
    recovery_key = f"password-recovery:testclient:{email}"

    redis_client.delete(recovery_key)

    payload = {
        "email": email,
    }

    first_response = client.post(
        "/api/v1/auth/forgot-password",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/auth/forgot-password",
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json() == {
        "detail": (
            "Too many password recovery attempts. "
            "Please try again later."
        ),
    }

    redis_client.delete(recovery_key)


def test_forgot_password_sends_reset_email(
    client,
    email_service,
    db_session,
):
    user = create_password_reset_test_user(db_session)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": user.email,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an account exists with that email, "
            "a password reset link has been sent."
        ),
    }

    assert len(email_service.sent_emails) == 1

    sent_email = email_service.sent_emails[0]

    assert sent_email["recipient"] == user.email
    assert sent_email["subject"] == "Reset your NexaWork password"
    assert "Reset your password using this link:" in sent_email["body"]
    assert "token=" in sent_email["body"]


def test_forgot_password_email_token_can_reset_password(
    client,
    email_service,
    db_session,
):
    user = create_password_reset_test_user(db_session)
    user.password_hash = hash_password("OldPassword123!")
    db_session.commit()

    forgot_response = client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": user.email,
        },
    )

    assert forgot_response.status_code == 200
    assert len(email_service.sent_emails) == 1

    sent_email = email_service.sent_emails[0]
    body = sent_email["body"]

    reset_url = next(
        line
        for line in body.splitlines()
        if "reset-password?token=" in line
    )

    raw_token = reset_url.split("token=", 1)[1]

    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewPassword123!",
        },
    )

    assert reset_response.status_code == 200
    assert reset_response.json() == {
        "message": "Password reset successful",
    }

    db_session.refresh(user)

    assert verify_password(
        "NewPassword123!",
        user.password_hash,
    )
    assert not verify_password(
        "OldPassword123!",
        user.password_hash,
    )
    assert user.token_version == 1


def test_public_registration_endpoint_is_removed(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "register.test@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "Registration Test User",
        },
    )

    assert response.status_code == 404
