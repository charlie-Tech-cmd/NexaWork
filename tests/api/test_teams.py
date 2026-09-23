from app.core.security.password import hash_password
from sqlalchemy import select
from app.models.branch import Branch
from app.models.department import Department
from app.models.organization import Organization
from app.models.region import Region
from app.models.team import Team
from app.models.user import User


def test_create_team_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-create-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-create-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-create-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-create-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="team.create@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "team.create@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/teams/departments/{department.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "department_id": department.id,
            "name": "Engineering Team",
            "slug": "engineering-team",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["department_id"] == department.id
    assert response_data["name"] == "Engineering Team"
    assert response_data["slug"] == "engineering-team"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None

    team = db_session.get(Team, response_data["id"])

    assert team is not None
    assert team.department_id == department.id
    assert team.name == "Engineering Team"
    assert team.slug == "engineering-team"

def test_create_team_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="team-create-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="team-create-b",
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
        email="team.create.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "team.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/teams/departments/{department_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "department_id": department_b.id,
            "name": "Unauthorized Team",
            "slug": "unauthorized-team",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}

    team = db_session.scalar(
        select(Team).where(Team.slug == "unauthorized-team")
    )

    assert team is None

def test_get_team_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-get-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-get-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-get-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-get-department",
    )
    db_session.add(department)
    db_session.flush()

    team = Team(
        department_id=department.id,
        name="Engineering Team",
        slug="engineering-team",
    )
    db_session.add(team)

    user = User(
        organization_id=organization.id,
        email="team.get@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "team.get@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/teams/{team.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == team.id
    assert response_data["department_id"] == department.id
    assert response_data["name"] == "Engineering Team"
    assert response_data["slug"] == "engineering-team"
    assert response_data["is_active"] is True


def test_get_team_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="team-get-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="team-get-b",
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
    db_session.flush()

    team_b = Team(
        department_id=department_b.id,
        name="Organization B Team",
        slug="organization-b-team",
    )
    db_session.add(team_b)

    user_a = User(
        organization_id=organization_a.id,
        email="team.get.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "team.get.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/teams/{team_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Team not found"}
