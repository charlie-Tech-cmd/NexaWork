from app.core.security.password import hash_password
from sqlalchemy import select
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User


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