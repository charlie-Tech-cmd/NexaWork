from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.user import User

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
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