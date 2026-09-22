from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.user import User


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

    response = client.post(
        "/auth/login",
        json={
            "email": "auth.test@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Login successful"
    assert data["id"] == user.id
    assert data["email"] == "auth.test@example.com"
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

    login_response = client.post(
        "/auth/login",
        json={
            "email": "me.test@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
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
        "/auth/me",
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

    login_response = client.post(
        "/auth/login",
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
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "User not found",
    }


def test_auth_me_rejects_missing_token(client):
    response = client.get("/auth/me")

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
        "/auth/me",
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
        "/auth/me",
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
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired token",
    }
