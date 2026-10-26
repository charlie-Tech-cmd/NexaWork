from sqlalchemy import select

from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.region import Region
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def _grant_region_permission(db_session, organization, user, permission_name):
    permission = Permission(
        name=permission_name,
        description=f"Test permission: {permission_name}",
        is_active=True,
    )
    role = Role(
        organization_id=organization.id,
        name=f"Region Test {permission_name}",
        description="Region API test role",
        is_active=True,
    )
    db_session.add_all([permission, role])
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


def test_get_region_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="region-api-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="region-api-b",
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
        email="region.api.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    _grant_region_permission(
        db_session, organization_a, user_a, "REGION_VIEW"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/regions/{region_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found"}


def test_get_region_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="current-region-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="current-organization-region",
    )
    db_session.add(region)

    user = User(
        organization_id=organization.id,
        email="current.region@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    _grant_region_permission(
        db_session, organization, user, "REGION_VIEW"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "current.region@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/regions/{region.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == region.id
    assert response_data["organization_id"] == organization.id
    assert response_data["name"] == "Current Organization Region"
    assert response_data["slug"] == "current-organization-region"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_get_region_rejects_inactive_region(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Region Organization",
        slug="inactive-region-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Region",
        slug="inactive-region",
        is_active=False,
    )
    db_session.add(region)

    user = User(
        organization_id=organization.id,
        email="inactive.region@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Region User",
        is_active=True,
    )
    db_session.add(user)
    _grant_region_permission(
        db_session, organization, user, "REGION_VIEW"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive.region@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/regions/{region.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found"}


def test_list_regions_excludes_inactive_region(
    client,
    db_session,
):
    organization = Organization(
        name="Region List Organization",
        slug="region-list-organization",
    )
    db_session.add(organization)
    db_session.flush()

    active_region = Region(
        organization_id=organization.id,
        name="Active Region",
        slug="active-region",
        is_active=True,
    )
    inactive_region = Region(
        organization_id=organization.id,
        name="Inactive Region",
        slug="inactive-region",
        is_active=False,
    )
    db_session.add_all([active_region, inactive_region])

    user = User(
        organization_id=organization.id,
        email="region.list@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Region List User",
        is_active=True,
    )
    db_session.add(user)
    _grant_region_permission(
        db_session, organization, user, "REGION_VIEW"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.list@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/regions/organizations/{organization.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 1
    assert response_data[0]["id"] == active_region.id
    assert response_data[0]["is_active"] is True


def test_list_regions_returns_only_current_organization_regions(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="region-list-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="region-list-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    region_a = Region(
        organization_id=organization_a.id,
        name="Organization A Region",
        slug="organization-a-region",
    )
    region_b = Region(
        organization_id=organization_b.id,
        name="Organization B Region",
        slug="organization-b-region",
    )
    db_session.add_all([region_a, region_b])

    user_a = User(
        organization_id=organization_a.id,
        email="region.list.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    _grant_region_permission(
        db_session, organization_a, user_a, "REGION_VIEW"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.list.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/regions/organizations/{organization_a.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 1
    assert response_data[0]["id"] == region_a.id
    assert response_data[0]["organization_id"] == organization_a.id
    assert response_data[0]["name"] == "Organization A Region"
    assert response_data[0]["slug"] == "organization-a-region"

def test_create_region_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="region-create-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="region-create-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="region.create.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    _grant_region_permission(
        db_session, organization_a, user_a, "REGION_CREATE"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/regions/organizations/{organization_b.id}",
        json={
            "name": "Unauthorized Region",
            "slug": "unauthorized-region",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}

    created_region = db_session.scalar(
        select(Region).where(Region.slug == "unauthorized-region")
    )

    assert created_region is None

def test_get_region_rejects_user_without_region_view_permission(
    client,
    db_session,
):
    organization = Organization(
        name="No Region View Organization",
        slug="no-region-view-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Protected Region",
        slug="protected-region",
    )
    user = User(
        organization_id=organization.id,
        email="no.region.view@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="No Region View User",
        is_active=True,
    )
    db_session.add_all([region, user])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "no.region.view@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    response = client.get(
        f"/api/v1/regions/{region.id}",
        headers={
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}


def test_create_region_allows_user_with_region_create_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Region Create Organization",
        slug="region-create-success-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="region.create.success@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Region Creator",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    _grant_region_permission(
        db_session, organization, user, "REGION_CREATE"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.create.success@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    response = client.post(
        f"/api/v1/regions/organizations/{organization.id}",
        json={
            "name": "New Test Region",
            "slug": "new-test-region",
        },
        headers={
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Test Region"
    assert data["slug"] == "new-test-region"
    assert data["organization_id"] == organization.id



def test_update_region_rejects_user_without_region_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="No Region Update Organization",
        slug="no-region-update-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Protected Region",
        slug="protected-region",
    )
    user = User(
        organization_id=organization.id,
        email="no.region.update@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="No Region Update User",
        is_active=True,
    )
    db_session.add_all([region, user])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "no.region.update@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    response = client.put(
        f"/api/v1/regions/{region.id}",
        json={"name": "Unauthorized Update"},
        headers={
            "Authorization": (
                f"Bearer {login_response.json()['access_token']}"
            )
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}

    db_session.refresh(region)
    assert region.name == "Protected Region"
    assert region.slug == "protected-region"


def test_update_region_allows_user_with_region_update_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Region Update Organization",
        slug="region-update-success-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Original Region",
        slug="original-region",
    )
    user = User(
        organization_id=organization.id,
        email="region.update.success@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Region Updater",
        is_active=True,
    )
    db_session.add_all([region, user])
    db_session.flush()

    _grant_region_permission(
        db_session, organization, user, "REGION_UPDATE"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.update.success@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    response = client.put(
        f"/api/v1/regions/{region.id}",
        json={"name": "Updated Region"},
        headers={
            "Authorization": (
                f"Bearer {login_response.json()['access_token']}"
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Region"
    assert response.json()["slug"] == "original-region"

    db_session.refresh(region)
    assert region.name == "Updated Region"

def test_list_regions_pagination_is_bounded_ordered_and_validated(
    client,
    db_session,
):
    organization = Organization(
        name="Region Pagination Organization",
        slug="region-pagination-org",
    )
    db_session.add(organization)
    db_session.flush()

    regions = [
        Region(
            organization_id=organization.id,
            name=f"Pagination Region {index:03d}",
            slug=f"pagination-region-{index:03d}",
            is_active=True,
        )
        for index in range(104)
    ]
    db_session.add_all(regions)

    user = User(
        organization_id=organization.id,
        email="region.pagination@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Region Pagination User",
        is_active=True,
    )
    db_session.add(user)
    _grant_region_permission(
        db_session, organization, user, "REGION_VIEW"
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "region.pagination@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }
    url = f"/api/v1/regions/organizations/{organization.id}"

    default_response = client.get(url, headers=headers)
    assert default_response.status_code == 200
    assert len(default_response.json()) == 50
    assert [region["id"] for region in default_response.json()] == sorted(
        region["id"] for region in default_response.json()
    )

    maximum_response = client.get(
        url,
        params={"limit": 100},
        headers=headers,
    )
    assert maximum_response.status_code == 200
    assert len(maximum_response.json()) == 100

    offset_response = client.get(
        url,
        params={"limit": 20, "offset": 50},
        headers=headers,
    )
    assert offset_response.status_code == 200
    assert len(offset_response.json()) == 20
    assert [region["id"] for region in offset_response.json()] == [
        region["id"] for region in maximum_response.json()
    ][50:70]

    assert client.get(
        url,
        params={"limit": 101},
        headers=headers,
    ).status_code == 422

    assert client.get(
        url,
        params={"limit": 0},
        headers=headers,
    ).status_code == 422

    assert client.get(
        url,
        params={"offset": -1},
        headers=headers,
    ).status_code == 422
