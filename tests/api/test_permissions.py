from app.core.security.password import hash_password
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.user import User


def test_update_permission_rejects_user_without_update_permission(
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

def test_update_permission_allows_user_with_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Permission Update Organization",
        slug="permission-update-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="TEST_PERMISSION",
        description="Original description",
    )
    update_permission = Permission(
        name="PERMISSION_UPDATE",
        description="Update permissions",
    )
    db_session.add_all([permission, update_permission])
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Permission Manager",
        description="Can update permissions",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="permission.manager@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permission Manager",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=update_permission.id,
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
            "email": "permission.manager@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/permissions/{permission.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "description": "Updated description",
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"

def test_create_permission_rejects_user_without_create_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Permission Create Reject Organization",
        slug="permission-create-reject-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="permission.create.reject@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permission Create Reject User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "permission.create.reject@example.com",
            "password": "SecurePassword123!",
        },
    )

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "NEW_PERMISSION",
            "description": "New permission",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }

def test_create_permission_allows_user_with_create_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Permission Create Organization",
        slug="permission-create-organization",
    )
    db_session.add(organization)
    db_session.flush()

    create_permission = Permission(
        name="PERMISSION_CREATE",
        description="Create permissions",
    )
    db_session.add(create_permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Permission Creator",
        description="Can create permissions",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="permission.creator@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permission Creator",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=create_permission.id,
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
            "email": "permission.creator@example.com",
            "password": "SecurePassword123!",
        },
    )

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "REPORT_VIEW",
            "description": "View reports",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "REPORT_VIEW"
    assert response.json()["description"] == "View reports"

def test_delete_permission_rejects_user_without_delete_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Permission Delete Reject Organization",
        slug="permission-delete-reject-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="DELETE_TEST_PERMISSION",
        description="Delete test permission",
    )
    db_session.add(permission)

    user = User(
        organization_id=organization.id,
        email="permission.delete.reject@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Delete Reject User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "permission.delete.reject@example.com",
            "password": "SecurePassword123!",
        },
    )

    access_token = login_response.json()["access_token"]

    response = client.delete(
        f"/api/v1/permissions/{permission.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }

def test_delete_permission_allows_user_with_delete_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Permission Delete Organization",
        slug="permission-delete-organization",
    )
    db_session.add(organization)
    db_session.flush()

    delete_permission = Permission(
        name="PERMISSION_DELETE",
        description="Delete permissions",
    )
    permission = Permission(
        name="DELETE_ME",
        description="Delete me",
    )

    db_session.add_all(
        [
            delete_permission,
            permission,
        ]
    )
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Permission Deleter",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="permission.deleter@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permission Deleter",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=delete_permission.id,
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
            "email": "permission.deleter@example.com",
            "password": "SecurePassword123!",
        },
    )

    access_token = login_response.json()["access_token"]

    response = client.delete(
        f"/api/v1/permissions/{permission.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204

    assert db_session.get(
        Permission,
        permission.id,
    ) is None                  

