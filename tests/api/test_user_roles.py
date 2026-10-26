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


def test_list_user_roles_rejects_user_without_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="List User Roles Security Organization",
        slug="list-user-roles-security-organization",
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
        name="User Updater",
        description="Can update users",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="list.user.roles.security@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="List User Roles Security Test",
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
            "email": "list.user.roles.security@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/users/{user.id}/roles",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_list_user_roles_allows_user_with_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="List User Roles Permission Organization",
        slug="list-user-roles-permission-organization",
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

    permission_role = Role(
        organization_id=organization.id,
        name="User Viewer",
        description="Role granting view permission",
        is_active=True,
    )
    db_session.add(permission_role)
    db_session.flush()

    target_role = Role(
        organization_id=organization.id,
        name="Assignable Role",
        description="Role assigned to the user",
        is_active=True,
    )
    db_session.add(target_role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="list.user.roles.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="List User Roles Permission Test",
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

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=target_role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "list.user.roles.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/users/{user.id}/roles",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    roles = response.json()

    assert len(roles) == 2
    assert {role["id"] for role in roles} == {
        permission_role.id,
        target_role.id,
    }

def test_normal_user_manager_cannot_assign_admin_enabled_role(
    client, db_session
):
    organization = Organization(
        name="Sensitive Assignment Organization",
        slug="sensitive-assignment-organization",
    )
    db_session.add(organization)
    db_session.flush()

    update_permission = Permission(
        name="USER_UPDATE", description="Update users", is_active=True
    )
    admin_permission = Permission(
        name="ADMIN_ACCESS", description="Admin access", is_active=True
    )
    manager_role = Role(
        organization_id=organization.id,
        name="Sensitive Assignment Manager",
        description="Ordinary user manager",
        is_active=True,
    )
    target_role = Role(
        organization_id=organization.id,
        name="Sensitive Assignment Target",
        description="Admin-enabled role",
        is_active=True,
    )
    user = User(
        organization_id=organization.id,
        email="sensitive.assignment.manager@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Sensitive Assignment Manager",
        is_active=True,
    )
    db_session.add_all([
        update_permission, admin_permission, manager_role, target_role, user
    ])
    db_session.flush()
    db_session.execute(role_permissions.insert().values(
        role_id=manager_role.id, permission_id=update_permission.id
    ))
    db_session.execute(role_permissions.insert().values(
        role_id=target_role.id, permission_id=admin_permission.id
    ))
    db_session.execute(user_roles.insert().values(
        user_id=user.id, role_id=manager_role.id
    ))
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={
        "email": "sensitive.assignment.manager@example.com",
        "password": "SecurePassword123!",
    })
    assert login.status_code == 200

    response = client.post(
        f"/api/v1/users/{user.id}/roles/{target_role.id}",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin authentication required"
    assignment = db_session.execute(user_roles.select().where(
        user_roles.c.user_id == user.id,
        user_roles.c.role_id == target_role.id,
    )).first()
    assert assignment is None


def test_assign_role_to_user_rejects_inactive_role(client, db_session):
    organization = Organization(
        name="Inactive Assignment Organization",
        slug="inactive-assignment-organization",
    )
    db_session.add(organization)
    db_session.flush()

    update_permission = Permission(
        name="USER_UPDATE", description="Update users", is_active=True
    )
    manager_role = Role(
        organization_id=organization.id,
        name="Inactive Assignment Manager",
        description="User manager",
        is_active=True,
    )
    target_role = Role(
        organization_id=organization.id,
        name="Inactive Assignment Target",
        description="Inactive role",
        is_active=False,
    )
    user = User(
        organization_id=organization.id,
        email="inactive.assignment.manager@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Assignment Manager",
        is_active=True,
    )
    db_session.add_all([update_permission, manager_role, target_role, user])
    db_session.flush()
    db_session.execute(role_permissions.insert().values(
        role_id=manager_role.id, permission_id=update_permission.id
    ))
    db_session.execute(user_roles.insert().values(
        user_id=user.id, role_id=manager_role.id
    ))
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={
        "email": "inactive.assignment.manager@example.com",
        "password": "SecurePassword123!",
    })
    assert login.status_code == 200

    response = client.post(
        f"/api/v1/users/{user.id}/roles/{target_role.id}",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot assign an inactive role"
    assignment = db_session.execute(user_roles.select().where(
        user_roles.c.user_id == user.id,
        user_roles.c.role_id == target_role.id,
    )).first()
    assert assignment is None


def test_normal_user_manager_cannot_assign_role_with_inactive_admin_access(
    client, db_session
):
    organization = Organization(
        name="Sensitive Assignment Organization",
        slug="sensitive-assignment-organization",
    )
    db_session.add(organization)
    db_session.flush()

    update_permission = Permission(
        name="USER_UPDATE", description="Update users", is_active=True
    )
    admin_permission = Permission(
        name="ADMIN_ACCESS", description="Admin access", is_active=False
    )
    manager_role = Role(
        organization_id=organization.id,
        name="Sensitive Assignment Manager",
        description="Ordinary user manager",
        is_active=True,
    )
    target_role = Role(
        organization_id=organization.id,
        name="Sensitive Assignment Target",
        description="Admin-enabled role",
        is_active=True,
    )
    user = User(
        organization_id=organization.id,
        email="sensitive.assignment.manager@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Sensitive Assignment Manager",
        is_active=True,
    )
    db_session.add_all([
        update_permission, admin_permission, manager_role, target_role, user
    ])
    db_session.flush()
    db_session.execute(role_permissions.insert().values(
        role_id=manager_role.id, permission_id=update_permission.id
    ))
    db_session.execute(role_permissions.insert().values(
        role_id=target_role.id, permission_id=admin_permission.id
    ))
    db_session.execute(user_roles.insert().values(
        user_id=user.id, role_id=manager_role.id
    ))
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={
        "email": "sensitive.assignment.manager@example.com",
        "password": "SecurePassword123!",
    })
    assert login.status_code == 200

    response = client.post(
        f"/api/v1/users/{user.id}/roles/{target_role.id}",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin authentication required"
    assignment = db_session.execute(user_roles.select().where(
        user_roles.c.user_id == user.id,
        user_roles.c.role_id == target_role.id,
    )).first()
    assert assignment is None


def test_admin_can_assign_admin_enabled_role_with_admin_token(
    client, db_session
):
    organization = Organization(
        name="Admin Assignment Success Organization",
        slug="admin-assignment-success-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user_permission = Permission(
        name="USER_UPDATE", description="Update users", is_active=True
    )
    admin_permission = Permission(
        name="ADMIN_ACCESS", description="Admin access", is_active=True
    )
    admin_role = Role(
        organization_id=organization.id,
        name="Admin Assignment Success Role",
        description="Administrator with user management",
        is_active=True,
    )
    target_role = Role(
        organization_id=organization.id,
        name="Admin Assignment Success Target",
        description="Admin-enabled target role",
        is_active=True,
    )
    admin_user = User(
        organization_id=organization.id,
        email="admin.assignment.success@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Admin Assignment Success",
        is_active=True,
    )
    target_user = User(
        organization_id=organization.id,
        email="admin.assignment.target@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Admin Assignment Target",
        is_active=True,
    )
    db_session.add_all([
        user_permission, admin_permission, admin_role,
        target_role, admin_user, target_user,
    ])
    db_session.flush()

    db_session.execute(role_permissions.insert().values(
        role_id=admin_role.id, permission_id=user_permission.id
    ))
    db_session.execute(role_permissions.insert().values(
        role_id=admin_role.id, permission_id=admin_permission.id
    ))
    db_session.execute(role_permissions.insert().values(
        role_id=target_role.id, permission_id=admin_permission.id
    ))
    db_session.execute(user_roles.insert().values(
        user_id=admin_user.id, role_id=admin_role.id
    ))
    db_session.commit()

    login = client.post("/api/v1/auth/admin/login", json={
        "email": admin_user.email,
        "password": "SecurePassword123!",
    })
    assert login.status_code == 200, login.text

    response = client.post(
        f"/api/v1/users/{target_user.id}/roles/{target_role.id}",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 204, response.text
    assignment = db_session.execute(user_roles.select().where(
        user_roles.c.user_id == target_user.id,
        user_roles.c.role_id == target_role.id,
    )).first()
    assert assignment is not None


def test_normal_user_manager_cannot_remove_admin_enabled_role(
    client, db_session
):
    organization = Organization(
        name="Sensitive Removal Organization",
        slug="sensitive-removal-organization",
    )
    db_session.add(organization)
    db_session.flush()

    update_permission = Permission(
        name="USER_UPDATE", description="Update users", is_active=True
    )
    admin_permission = Permission(
        name="ADMIN_ACCESS", description="Admin access", is_active=True
    )
    manager_role = Role(
        organization_id=organization.id,
        name="Sensitive Removal Manager",
        description="Ordinary user manager",
        is_active=True,
    )
    target_role = Role(
        organization_id=organization.id,
        name="Sensitive Removal Target",
        description="Admin-enabled role",
        is_active=True,
    )
    user = User(
        organization_id=organization.id,
        email="sensitive.removal.manager@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Sensitive Removal Manager",
        is_active=True,
    )
    db_session.add_all([
        update_permission, admin_permission, manager_role, target_role, user
    ])
    db_session.flush()

    db_session.execute(role_permissions.insert().values(
        role_id=manager_role.id, permission_id=update_permission.id
    ))
    db_session.execute(role_permissions.insert().values(
        role_id=target_role.id, permission_id=admin_permission.id
    ))
    db_session.execute(user_roles.insert().values(
        user_id=user.id, role_id=manager_role.id
    ))
    db_session.execute(user_roles.insert().values(
        user_id=user.id, role_id=target_role.id
    ))
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={
        "email": "sensitive.removal.manager@example.com",
        "password": "SecurePassword123!",
    })
    assert login.status_code == 200

    response = client.delete(
        f"/api/v1/users/{user.id}/roles/{target_role.id}",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin authentication required"

    assignment = db_session.execute(user_roles.select().where(
        user_roles.c.user_id == user.id,
        user_roles.c.role_id == target_role.id,
    )).first()
    assert assignment is not None
