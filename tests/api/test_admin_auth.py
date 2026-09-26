from app.core.security.password import hash_password

from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def test_employee_cannot_login_as_admin(
    client,
    db_session,
):
    organization = Organization(
        name="Admin Auth Test Organization",
        slug="admin-auth-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee.admin@test.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Normal Employee",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": "employee.admin@test.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Admin access required",
    }

def test_admin_login_succeeds_with_admin_access_permission(
    client,
    db_session,
):
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

    admin_role = Role(
        organization_id=organization.id,
        name="Organization Admin",
        description="Administrator role",
        is_active=True,
    )

    user = User(
        organization_id=organization.id,
        email="admin@test.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Admin",
        is_active=True,
    )

    db_session.add_all(
        [
            permission,
            admin_role,
            user,
        ]
    )

    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=admin_role.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=admin_role.id,
        )
    )

    db_session.commit()

    response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": "admin@test.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Admin login successful"
    assert data["email"] == "admin@test.com"
    assert "access_token" in data