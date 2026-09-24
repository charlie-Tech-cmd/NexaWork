from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.user import User
from app.models.permission import Permission
from sqlalchemy import select
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles


def test_list_users_rejects_user_without_permission(client, db_session):
    organization = Organization(
        name="Users API Test Organization",
        slug="users-api-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="users.api.test@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Users API Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "users.api.test@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission denied",
    }


def test_list_users_allows_user_with_view_permission(client, db_session):
    organization = Organization(
        name="Authorized Users API Organization",
        slug="authorized-users-api-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="USER_VIEW",
        description="View users",
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
        email="authorized.users@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Authorized Users Test",
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
            "email": "authorized.users@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": user.id,
            "email": "authorized.users@example.com",
            "full_name": "Authorized Users Test",
            "is_active": True,
        }
    ]


def test_get_user_rejects_user_from_another_organization(client, db_session):
    organization_a = Organization(
        name="Organization A",
        slug="users-api-organization-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="users-api-organization-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    permission = Permission(
        name="USER_VIEW",
        description="View users",
    )
    db_session.add(permission)
    db_session.flush()

    role_a = Role(
        organization_id=organization_a.id,
        name="Organization A Viewer",
        is_active=True,
    )
    db_session.add(role_a)
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="organization.a.viewer@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A Viewer",
        is_active=True,
    )
    user_b = User(
        organization_id=organization_b.id,
        email="organization.b.user@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization B User",
        is_active=True,
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role_a.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user_a.id,
            role_id=role_a.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "organization.a.viewer@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/users/{user_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "User not found",
    }


def test_create_user_assigns_authenticated_users_organization(
    client,
    db_session,
):
    organization = Organization(
        name="User Creation Organization",
        slug="user-creation-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="USER_CREATE",
        description="Create users",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="User Creator",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    admin = User(
        organization_id=organization.id,
        email="user.creator@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="User Creator",
        is_active=True,
    )
    db_session.add(admin)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=admin.id,
            role_id=role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user.creator@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "email": "created.user@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "Created User",
        },
    )

    assert response.status_code == 201

    created_user = db_session.scalar(
        select(User).where(User.email == "created.user@example.com")
    )

    assert created_user is not None
    assert created_user.organization_id == organization.id


def test_update_user_rejects_user_from_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Update Organization A",
        slug="update-organization-a",
    )
    organization_b = Organization(
        name="Update Organization B",
        slug="update-organization-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    permission = Permission(
        name="USER_UPDATE",
        description="Update users",
    )
    db_session.add(permission)
    db_session.flush()

    role_a = Role(
        organization_id=organization_a.id,
        name="Organization A Updater",
        is_active=True,
    )
    db_session.add(role_a)
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="organization.a.updater@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A Updater",
        is_active=True,
    )
    user_b = User(
        organization_id=organization_b.id,
        email="organization.b.target@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization B Target",
        is_active=True,
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role_a.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user_a.id,
            role_id=role_a.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "organization.a.updater@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/users/{user_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "full_name": "Unauthorized Cross-Tenant Update",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "User not found",
    }

    db_session.refresh(user_b)

    assert user_b.full_name == "Organization B Target"


def test_deactivate_user_rejects_user_from_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Deactivate Organization A",
        slug="deactivate-organization-a",
    )
    organization_b = Organization(
        name="Deactivate Organization B",
        slug="deactivate-organization-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    permission = Permission(
        name="USER_DELETE",
        description="Deactivate users",
    )
    db_session.add(permission)
    db_session.flush()

    role_a = Role(
        organization_id=organization_a.id,
        name="Organization A Deactivator",
        is_active=True,
    )
    db_session.add(role_a)
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="organization.a.deactivator@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A Deactivator",
        is_active=True,
    )
    user_b = User(
        organization_id=organization_b.id,
        email="organization.b.target@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization B Target",
        is_active=True,
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role_a.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user_a.id,
            role_id=role_a.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "organization.a.deactivator@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.request(
        "DELETE",
        f"/api/v1/users/{user_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "User not found",
    }

    db_session.refresh(user_b)

    assert user_b.is_active is True
