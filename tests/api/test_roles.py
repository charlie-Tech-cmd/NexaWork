from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles
from app.models.role import Role


def test_create_role_rejects_user_without_create_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role API Test Organization",
        slug="role-api-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="role.user@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.user@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/roles",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "name": "HR Manager",
            "description": "HR access role",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_create_role_allows_user_with_create_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Create Organization",
        slug="role-create-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="ROLE_CREATE",
        description="Create roles",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Role Manager",
        description="Can create roles",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="role.manager@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Manager",
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
            "email": "role.manager@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/roles",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "name": "HR Manager",
            "description": "HR access role",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "HR Manager"

def test_update_role_rejects_user_without_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Update Test Organization",
        slug="role-update-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Original Role",
        description="Original description",
        is_active=True,
    )
    db_session.add(role)

    user = User(
        organization_id=organization.id,
        email="role.update.user@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Update User",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.update.user@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/roles/{role.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "description": "Updated description",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_update_role_allows_user_with_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Update Allowed Organization",
        slug="role-update-allowed-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="ROLE_UPDATE",
        description="Update roles",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    manager_role = Role(
        organization_id=organization.id,
        name="Role Manager",
        description="Can update roles",
        is_active=True,
    )
    db_session.add(manager_role)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Role",
        description="Original description",
        is_active=True,
    )
    db_session.add(role)

    user = User(
        organization_id=organization.id,
        email="role.manager.update@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Update Manager",
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=manager_role.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=manager_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.manager.update@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/roles/{role.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "description": "Updated description",
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"

def test_list_roles_rejects_user_without_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role View Test Organization",
        slug="role-view-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="role.viewer.denied@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Viewer Denied",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.viewer.denied@example.com",
            "password": "SecurePassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/roles",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_list_roles_allows_user_with_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role View Allowed Organization",
        slug="role-view-allowed-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="ROLE_VIEW",
        description="View roles",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    manager_role = Role(
        organization_id=organization.id,
        name="Role Viewer",
        description="Can view roles",
        is_active=True,
    )
    db_session.add(manager_role)
    db_session.flush()

    target_role = Role(
        organization_id=organization.id,
        name="Employee",
        description="Employee role",
        is_active=True,
    )
    db_session.add(target_role)

    user = User(
        organization_id=organization.id,
        email="role.viewer.allowed@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Viewer Allowed",
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=manager_role.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=manager_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.viewer.allowed@example.com",
            "password": "SecurePassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/roles",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    roles = response.json()

    assert any(
        role["name"] == "Employee"
        for role in roles
    )

def test_assign_permission_to_role_rejects_without_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Permission Denied Organization",
        slug="role-permission-denied-organization",
    )
    db_session.add(organization)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee",
        description="Employee role",
        is_active=True,
    )

    permission = Permission(
        name="TEST_ACCESS",
        description="Test access permission",
        is_active=True,
    )

    user = User(
        organization_id=organization.id,
        email="permission.assign.denied@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permission Assign Denied",
        is_active=True,
    )

    db_session.add_all([role, permission, user])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "permission.assign.denied@example.com",
            "password": "SecurePassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/roles/{role.id}/permissions/{permission.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }

def test_assign_permission_to_role_allows_with_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Permission Allowed Organization",
        slug="role-permission-allowed-organization",
    )
    db_session.add(organization)
    db_session.flush()

    update_permission = Permission(
        name="ROLE_UPDATE",
        description="Update roles",
        is_active=True,
    )

    assigned_permission = Permission(
        name="TEST_ACCESS",
        description="Test access permission",
        is_active=True,
    )

    manager_role = Role(
        organization_id=organization.id,
        name="Role Manager",
        description="Can manage roles",
        is_active=True,
    )

    db_session.add_all(
        [
            update_permission,
            assigned_permission,
            manager_role,
        ]
    )
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="permission.assign.allowed@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Permission Assign Allowed",
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=manager_role.id,
            permission_id=update_permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=manager_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "permission.assign.allowed@example.com",
            "password": "SecurePassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/roles/{manager_role.id}/permissions/{assigned_permission.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 204

    assignment = db_session.execute(
        role_permissions.select().where(
            role_permissions.c.role_id == manager_role.id,
            role_permissions.c.permission_id == assigned_permission.id,
        )
    ).first()

    assert assignment is not None

def test_list_role_permissions_allows_with_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Permission View Organization",
        slug="role-permission-view-organization",
    )
    db_session.add(organization)
    db_session.flush()

    view_permission = Permission(
        name="ROLE_VIEW",
        description="View roles",
        is_active=True,
    )

    assigned_permission = Permission(
        name="TEST_PERMISSION",
        description="Test permission",
        is_active=True,
    )

    viewer_role = Role(
        organization_id=organization.id,
        name="Role Viewer",
        description="Can view roles",
        is_active=True,
    )

    db_session.add_all(
        [
            view_permission,
            assigned_permission,
            viewer_role,
        ]
    )
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="role.permission.viewer@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Permission Viewer",
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=viewer_role.id,
            permission_id=view_permission.id,
        )
    )

    db_session.execute(
        role_permissions.insert().values(
            role_id=viewer_role.id,
            permission_id=assigned_permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=viewer_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.permission.viewer@example.com",
            "password": "SecurePassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/roles/{viewer_role.id}/permissions",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    permissions = response.json()

    assert any(
        permission["name"] == "TEST_PERMISSION"
        for permission in permissions
    )

def test_remove_permission_from_role_allows_with_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Role Permission Remove Organization",
        slug="role-permission-remove-organization",
    )
    db_session.add(organization)
    db_session.flush()

    update_permission = Permission(
        name="ROLE_UPDATE",
        description="Update roles",
        is_active=True,
    )

    removable_permission = Permission(
        name="TEST_REMOVE_PERMISSION",
        description="Remove test permission",
        is_active=True,
    )

    manager_role = Role(
        organization_id=organization.id,
        name="Role Manager",
        description="Can update roles",
        is_active=True,
    )

    db_session.add_all(
        [
            update_permission,
            removable_permission,
            manager_role,
        ]
    )
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="role.permission.remove@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Role Permission Remove",
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=manager_role.id,
            permission_id=update_permission.id,
        )
    )

    db_session.execute(
        role_permissions.insert().values(
            role_id=manager_role.id,
            permission_id=removable_permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=manager_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "role.permission.remove@example.com",
            "password": "SecurePassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.delete(
        f"/api/v1/roles/{manager_role.id}/permissions/{removable_permission.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 204

    assignment = db_session.execute(
        role_permissions.select().where(
            role_permissions.c.role_id == manager_role.id,
            role_permissions.c.permission_id == removable_permission.id,
        )
    ).first()

    assert assignment is None                        