from sqlalchemy import select
from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def test_remove_role_from_user_rejects_user_without_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="User Roles Security Organization",
        slug="user-roles-security-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="USER_VIEW",
        description="View users",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="User Viewer",
        description="Can view users",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="user.roles.security@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="User Roles Security Test",
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

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user.roles.security@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.delete(
        f"/api/v1/users/{user.id}/roles/{role.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_remove_role_from_user_allows_user_with_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Authorized User Roles Organization",
        slug="authorized-user-roles-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="USER_UPDATE",
        description="Update users",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="User Manager",
        description="Can manage users",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="authorized.user.roles@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Authorized User Roles Test",
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

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "authorized.user.roles@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.delete(
        f"/api/v1/users/{user.id}/roles/{role.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204

    assignment = db_session.execute(
        select(user_roles).where(
            user_roles.c.user_id == user.id,
            user_roles.c.role_id == role.id,
        )
    ).first()

    assert assignment is None

def test_assign_role_to_user_rejects_user_without_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Assign Role Security Organization",
        slug="assign-role-security-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="USER_VIEW",
        description="View users",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Assignable Role",
        description="Role for assignment security test",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="assign.role.security@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Assign Role Security Test",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()


    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "assign.role.security@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]
    response = client.post(
        f"/api/v1/users/{user.id}/roles/{role.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_assign_role_to_user_allows_user_with_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Assign Role Permission Organization",
        slug="assign-role-permission-organization",
    )
    db_session.add(organization)
    db_session.flush()


    permission = Permission(
        name="USER_UPDATE",
        description="Update users",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    permission_role = Role(
        organization_id=organization.id,
        name="User Manager",
        description="Role granting assignment permission",
        is_active=True,
    )
    db_session.add(permission_role)
    db_session.flush()

    target_role = Role(
        organization_id=organization.id,
        name="Assignable Role",
        description="Role being assigned",
        is_active=True,
    )
    db_session.add(target_role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="assign.role.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Assign Role Permission Test",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()


    db_session.execute(
        role_permissions.insert().values(
            role_id=permission_role.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=permission_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "assign.role.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/users/{user.id}/roles/{target_role.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204

    assignment = db_session.execute(
        select(user_roles).where(
            user_roles.c.user_id == user.id,
            user_roles.c.role_id == target_role.id,
        )
    ).first()

    assert assignment is not None
