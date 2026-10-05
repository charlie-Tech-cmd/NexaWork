from app.core.security.password import hash_password
from sqlalchemy import select

from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def test_get_organization_blocks_cross_organization_access(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="organization-api-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="organization-api-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()
    user_a = User(
        organization_id=organization_a.id,
        email="organization.api.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "organization.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/organizations/{organization_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Organization not found",
    }


def test_get_organization_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="current-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="current.organization@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "current.organization@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/organizations/{organization.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == organization.id
    assert response_data["name"] == "Current Organization"
    assert response_data["slug"] == "current-organization"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_get_my_organization_returns_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="My Organization",
        slug="my-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="my.organization@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="My Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "my.organization@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == organization.id
    assert response_data["name"] == "My Organization"
    assert response_data["slug"] == "my-organization"
    assert response_data["is_active"] is True


def test_inactive_organization_blocks_current_user(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Organization",
        slug="inactive-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.organization@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive.organization@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    organization.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization is inactive or unavailable",
    }


def test_reactivated_organization_restores_current_user_access(
    client,
    db_session,
):
    organization = Organization(
        name="Reactivated Organization",
        slug="reactivated-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="reactivated.organization@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Reactivated Organization User",
        is_active=True,
    )
    db_session.add(user)

    super_admin = User(
        organization_id=None,
        email="reactivated.superadmin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Reactivated Super Admin",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    user_login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "reactivated.organization@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert user_login_response.status_code == 200

    user_access_token = user_login_response.json()["access_token"]

    organization.is_active = False
    db_session.commit()

    blocked_response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )

    assert blocked_response.status_code == 403
    assert blocked_response.json() == {
        "detail": "Organization is inactive or unavailable",
    }

    super_admin_login_response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": "reactivated.superadmin@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert super_admin_login_response.status_code == 200

    super_admin_access_token = super_admin_login_response.json()[
        "access_token"]

    reactivate_response = client.patch(
        f"/api/v1/organizations/{organization.id}/status",
        headers={
            "Authorization": f"Bearer {super_admin_access_token}",
        },
        json={"is_active": True},
    )

    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True

    db_session.refresh(organization)
    assert organization.is_active is True

    restored_response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )

    assert restored_response.status_code == 200
    assert restored_response.json()["id"] == organization.id
    assert restored_response.json()["is_active"] is True


def test_update_my_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Original Organization",
        slug="original-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="organization.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="ORGANIZATION_UPDATE",
        description="Update organization settings",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Organization Admin",
        description="Manage organization",
        is_active=True,
    )
    db_session.add(role)
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
            "email": "organization.admin@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Updated Organization",
            "slug": "updated-organization",
        },
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["id"] == organization.id
    assert response_data["name"] == "Updated Organization"
    assert response_data["slug"] == "updated-organization"


def test_update_my_organization_requires_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Protected Organization",
        slug="protected-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Regular Employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Unauthorized Update",
        },
    )

    assert response.status_code == 403

    db_session.refresh(organization)
    assert organization.name == "Protected Organization"


def test_update_my_organization_requires_at_least_one_field(
    client,
    db_session,
):
    organization = Organization(
        name="Validation Organization",
        slug="validation-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="validation.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Validation Admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="ORGANIZATION_UPDATE",
        description="Update organization settings",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Organization Admin",
        description="Manage organization",
        is_active=True,
    )
    db_session.add(role)
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
            "email": "validation.admin@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
    )

    assert response.status_code == 422

    db_session.refresh(organization)
    assert organization.name == "Validation Organization"
    assert organization.slug == "validation-organization"


def test_update_my_organization_rejects_duplicate_slug(
    client,
    db_session,
):
    organization = Organization(
        name="Primary Organization",
        slug="primary-organization",
    )
    existing_organization = Organization(
        name="Existing Organization",
        slug="existing-organization",
    )
    db_session.add_all([organization, existing_organization])
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="slug.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Slug Admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="ORGANIZATION_UPDATE",
        description="Update organization settings",
        is_active=True,
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Organization Admin",
        description="Manage organization",
        is_active=True,
    )
    db_session.add(role)
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
            "email": "slug.admin@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "slug": "existing-organization",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Organization slug already exists"

    db_session.refresh(organization)
    assert organization.slug == "primary-organization"


def test_create_organization_requires_super_admin(
    client,
    db_session,
):
    organization = Organization(
        name="Existing Organization",
        slug="existing-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="regular.user@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Regular User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "regular.user@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Unauthorized Organization",
            "slug": "unauthorized-organization",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Super Admin authentication required",
    }

    created_organization = db_session.scalar(
        select(Organization).where(
            Organization.slug == "unauthorized-organization",
        )
    )
    assert created_organization is None


def test_create_organization_allows_super_admin(
    client,
    db_session,
):
    super_admin = User(
        organization_id=None,
        email="super.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Super Admin",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": "super.admin@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Super Admin Organization",
            "slug": "super-admin-organization",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "Super Admin Organization"
    assert response_data["slug"] == "super-admin-organization"
    assert response_data["is_active"] is True

    created_organization = db_session.scalar(
        select(Organization).where(
            Organization.slug == "super-admin-organization",
        )
    )
    assert created_organization is not None
    assert created_organization.name == "Super Admin Organization"

def test_organization_onboarding_grants_organization_update_permission(
    client,
    db_session,
):
    db_session.add_all(
        [
            Permission(
                name="USER_VIEW",
                description="View users",
                is_active=True,
            ),
            Permission(
                name="USER_CREATE",
                description="Create users",
                is_active=True,
            ),
            Permission(
                name="USER_UPDATE",
                description="Update users",
                is_active=True,
            ),
            Permission(
                name="USER_DELETE",
                description="Delete users",
                is_active=True,
            ),
            Permission(
                name="ORGANIZATION_UPDATE",
                description="Update organization settings",
                is_active=True,
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/organizations/onboard",
        json={
            "organization_name": "Onboarding Organization",
            "organization_slug": "onboarding-organization",
            "admin_email": "onboarding.admin@example.com",
            "admin_password": "SecurePassword123!",
            "admin_confirm_password": "SecurePassword123!",
            "admin_full_name": "Onboarding Admin",
        },
    )

    assert response.status_code == 201

    response_data = response.json()
    organization_id = response_data["organization"]["id"]
    admin_id = response_data["admin"]["id"]

    organization_admin_role = db_session.scalar(
        select(Role).where(
            Role.organization_id == organization_id,
            Role.name == "Organization Admin",
        )
    )
    assert organization_admin_role is not None

    admin_permission = db_session.scalar(
        select(Permission).where(
            Permission.name == "ORGANIZATION_UPDATE",
        )
    )
    assert admin_permission is not None

    permission_exists = db_session.scalar(
        select(role_permissions.c.role_id).where(
            role_permissions.c.role_id == organization_admin_role.id,
            role_permissions.c.permission_id == admin_permission.id,
        )
    )
    assert permission_exists == organization_admin_role.id

    user_role_exists = db_session.scalar(
        select(user_roles.c.user_id).where(
            user_roles.c.user_id == admin_id,
            user_roles.c.role_id == organization_admin_role.id,
        )
    )
    assert user_role_exists == admin_id


def test_update_organization_status_requires_super_admin(
    client,
    db_session,
):
    organization = Organization(
        name="Status Protected Organization",
        slug="status-protected-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="status.user@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "status.user@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        f"/api/v1/organizations/{organization.id}/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Super Admin authentication required",
    }

    db_session.refresh(organization)
    assert organization.is_active is True


def test_update_organization_status_allows_super_admin(
    client,
    db_session,
):
    organization = Organization(
        name="Status Organization",
        slug="status-organization",
    )
    db_session.add(organization)

    super_admin = User(
        organization_id=None,
        email="status.superadmin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Status Super Admin",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": "status.superadmin@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        f"/api/v1/organizations/{organization.id}/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )

    assert response.status_code == 200

    response_data = response.json()
    assert response_data["id"] == organization.id
    assert response_data["is_active"] is False

    db_session.refresh(organization)
    assert organization.is_active is False


def test_update_organization_status_rejects_missing_organization(
    client,
    db_session,
):
    super_admin = User(
        organization_id=None,
        email="missing.status.superadmin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Missing Status Super Admin",
        is_active=True,
        is_super_admin=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/super-admin/login",
        json={
            "email": "missing.status.superadmin@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/organizations/999999/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Organization not found",
    }
