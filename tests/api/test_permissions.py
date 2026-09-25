from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.user import User


def test_update_permission_rejects_user_without_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Permissions API Test Organization",
        slug="permissions-api-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="TEST_PERMISSION",
        description="Test permission",
    )
    db_session.add(permission)

    user = User(
        organization_id=organization.id,
        email="permissions.api.test@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permissions API Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "permissions.api.test@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/permissions/{permission.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"description": "Updated permission"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }
