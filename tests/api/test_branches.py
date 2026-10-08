from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.region import Region
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles
from sqlalchemy import select


def grant_permission(db_session, user, permission_name):
    permission = Permission(
        name=permission_name,
        description=f"{permission_name} test permission",
    )
    db_session.add(permission)
    db_session.flush()
    role = Role(
        organization_id=user.organization_id,
        name=f"{permission_name} Test Role",
        description=f"Test role for {permission_name}",
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
def test_get_branch_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="branch-api-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="branch-api-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()
    region_b = Region(
        organization_id=organization_b.id,
        name="Organization B Region",
        slug="organization-b-region",
    )
    db_session.add(region_b)
    db_session.flush()
    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Organization B Branch",
        slug="organization-b-branch",
    )
    db_session.add(branch_b)
    user_a = User(
        organization_id=organization_a.id,
        email="branch.api.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    grant_permission(db_session, user_a, "BRANCH_VIEW")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "branch.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/branches/{branch_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}


def test_get_branch_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="current-branch-organization",
    )
    db_session.add(organization)
    db_session.flush()
    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="current-organization-region",
    )
    db_session.add(region)
    db_session.flush()
    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="current-organization-branch",
    )
    db_session.add(branch)
    user = User(
        organization_id=organization.id,
        email="current.branch@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    grant_permission(db_session, user, "BRANCH_VIEW")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "current.branch@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/branches/{branch.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == branch.id
    assert response_data["region_id"] == region.id
    assert response_data["name"] == "Current Organization Branch"
    assert response_data["slug"] == "current-organization-branch"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_list_branches_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="branch-list-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="branch-list-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()
    region_b = Region(
        organization_id=organization_b.id,
        name="Organization B Region",
        slug="organization-b-region",
    )
    db_session.add(region_b)
    db_session.flush()
    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Organization B Branch",
        slug="organization-b-branch",
    )
    db_session.add(branch_b)
    user_a = User(
        organization_id=organization_a.id,
        email="branch.list.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    grant_permission(db_session, user_a, "BRANCH_VIEW")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "branch.list.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/branches/regions/{region_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found"}


def test_create_branch_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="branch-create-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="branch-create-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()
    region_b = Region(
        organization_id=organization_b.id,
        name="Organization B Region",
        slug="organization-b-region",
    )
    db_session.add(region_b)
    user_a = User(
        organization_id=organization_a.id,
        email="branch.create.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    grant_permission(db_session, user_a, "BRANCH_CREATE")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "branch.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/branches/regions/{region_b.id}",
        json={
            "name": "Unauthorized Branch",
            "slug": "unauthorized-branch",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found"}

    created_branch = db_session.scalar(
        select(Branch).where(Branch.slug == "unauthorized-branch")
    )

    assert created_branch is None


def test_create_branch_rejects_inactive_region(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Region Organization",
        slug="inactive-region-create-org",
    )
    db_session.add(organization)
    db_session.flush()
    region = Region(
        organization_id=organization.id,
        name="Inactive Region",
        slug="inactive-region-create",
        is_active=False,
    )
    db_session.add(region)
    user = User(
        organization_id=organization.id,
        email="inactive.region.create@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Region Create User",
        is_active=True,
    )
    db_session.add(user)
    grant_permission(db_session, user, "BRANCH_CREATE")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive.region.create@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/branches/regions/{region.id}",
        json={
            "name": "Blocked Branch",
            "slug": "blocked-branch",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found"}

    created_branch = db_session.scalar(
        select(Branch).where(Branch.slug == "blocked-branch")
    )

    assert created_branch is None


def test_list_branches_rejects_inactive_region(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Region List Organization",
        slug="inactive-region-list-org",
    )
    db_session.add(organization)
    db_session.flush()
    region = Region(
        organization_id=organization.id,
        name="Inactive Region",
        slug="inactive-region-list",
        is_active=False,
    )
    db_session.add(region)
    db_session.flush()
    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Region Branch",
        slug="inactive-region-branch",
    )
    db_session.add(branch)
    user = User(
        organization_id=organization.id,
        email="inactive.region.list@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Region List User",
        is_active=True,
    )
    db_session.add(user)
    grant_permission(db_session, user, "BRANCH_VIEW")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive.region.list@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/branches/regions/{region.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found"}
