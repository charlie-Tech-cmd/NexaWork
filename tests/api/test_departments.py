from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.department import Department
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User
from sqlalchemy import select


def test_get_department_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="department-api-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="department-api-b",
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
    db_session.flush()

    department_b = Department(
        branch_id=branch_b.id,
        name="Organization B Department",
        slug="organization-b-department",
    )
    db_session.add(department_b)

    user_a = User(
        organization_id=organization_a.id,
        email="department.api.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "department.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/departments/{department_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}


def test_get_department_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="current-department-organization",
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
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="current-organization-department",
    )
    db_session.add(department)

    user = User(
        organization_id=organization.id,
        email="current.department@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "current.department@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/departments/{department.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == department.id
    assert response_data["branch_id"] == branch.id
    assert response_data["name"] == "Current Organization Department"
    assert response_data["slug"] == "current-organization-department"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_list_departments_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="department-list-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="department-list-b",
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
        email="department.list.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "department.list.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/departments/branches/{branch_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}


def test_create_department_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="department-create-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="department-create-b",
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
        email="department.create.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "department.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/departments/branches/{branch_b.id}",
        json={
            "name": "Unauthorized Department",
            "slug": "unauthorized-department",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}

    created_department = db_session.scalar(
        select(Department).where(
            Department.slug == "unauthorized-department"
        )
    )

    assert created_department is None