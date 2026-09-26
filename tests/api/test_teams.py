from app.core.security.password import hash_password
from sqlalchemy import select
from app.models.branch import Branch
from app.models.department import Department
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
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
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-branch",
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

    permission = Permission(
        name="TEAM_CREATE",
        description="Create teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Team Creator",
        description="Can create teams",
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
            "email": "team.create@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/teams/departments/{department.id}",
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
        email="team.create.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)

    permission = Permission(
        name="TEAM_CREATE",
        description="Create teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Team Creator",
        description="Can create teams",
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
            user_id=user_a.id,
            role_id=role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/teams/departments/{department_b.id}",
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
        organization_id=organization.id,
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

    permission = Permission(
        name="TEAM_VIEW",
        description="View teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Team Viewer",
        description="Can view teams",
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
            "email": "team.get@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/teams/{team.id}",
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

    permission = Permission(
        name="TEAM_VIEW",
        description="View teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Team Viewer",
        description="Can view teams",
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
            user_id=user_a.id,
            role_id=role.id,
        )
    )

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.get.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/teams/{team_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Team not found"}


def test_list_teams_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-list-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-list-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="...",
    )

    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-list-department",
    )
    db_session.add(department)
    db_session.flush()

    team_one = Team(
        department_id=department.id,
        name="Engineering Team",
        slug="engineering-team",
    )
    team_two = Team(
        department_id=department.id,
        name="Product Team",
        slug="product-team",
    )
    db_session.add_all([team_one, team_two])

    user = User(
        organization_id=organization.id,
        email="team.list@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="TEAM_VIEW",
        description="View teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Team Viewer",
        description="Can view teams",
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
            "email": "team.list@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/teams/departments/{department.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 2
    assert [team["id"] for team in response_data] == [
        team_one.id,
        team_two.id,
    ]
    assert [team["name"] for team in response_data] == [
        "Engineering Team",
        "Product Team",
    ]


def test_list_teams_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="team-list-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="team-list-b",
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
    db_session.flush()

    team_b = Team(
        department_id=department_b.id,
        name="Organization B Team",
        slug="organization-b-team",
    )
    db_session.add(team_b)

    user_a = User(
        organization_id=organization_a.id,
        email="team.list.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    permission = Permission(
        name="TEAM_VIEW",
        description="View teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Team Viewer",
        description="Can view teams",
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
            user_id=user_a.id,
            role_id=role.id,
        )
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.list.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/teams/departments/{department_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}

def test_update_team_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-update-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-update-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-update-branch",
    )

    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-update-department",
    )
    db_session.add(department)
    db_session.flush()

    team = Team(
        department_id=department.id,
        name="Old Team Name",
        slug="old-team-slug",
    )
    db_session.add(team)

    user = User(
        organization_id=organization.id,
        email="team.update@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="TEAM_UPDATE",
        description="Update teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Team Updater",
        description="Can update teams",
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
            "email": "team.update@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/teams/{team.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Updated Team Name",
            "slug": "updated-team-slug",
            "is_active": False,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == team.id
    assert response_data["name"] == "Updated Team Name"
    assert response_data["slug"] == "updated-team-slug"
    assert response_data["is_active"] is False

    db_session.refresh(team)

    assert team.name == "Updated Team Name"
    assert team.slug == "updated-team-slug"
    assert team.is_active is False


def test_update_team_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="team-update-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="team-update-b",
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
    db_session.flush()

    team_b = Team(
        department_id=department_b.id,
        name="Organization B Team",
        slug="organization-b-team",
    )
    db_session.add(team_b)

    user_a = User(
        organization_id=organization_a.id,
        email="team.update.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    permission = Permission(
        name="TEAM_UPDATE",
        description="Update teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Team Updater",
        description="Can update teams",
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
            user_id=user_a.id,
            role_id=role.id,
        )
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.update.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/teams/{team_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Unauthorized Update",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Team not found"}

    db_session.refresh(team_b)

    assert team_b.name == "Organization B Team"


def test_update_team_rejects_duplicate_slug(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-update-duplicate",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-update-duplicate-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-update-duplicate-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-update-duplicate-department",
    )
    db_session.add(department)
    db_session.flush()

    team_one = Team(
        department_id=department.id,
        name="Engineering Team",
        slug="engineering-team",
    )
    team_two = Team(
        department_id=department.id,
        name="Product Team",
        slug="product-team",
    )
    db_session.add_all([team_one, team_two])

    user = User(
        organization_id=organization.id,
        email="team.update.duplicate@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="TEAM_UPDATE",
        description="Update teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Team Updater",
        description="Can update teams",
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
            "email": "team.update.duplicate@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/teams/{team_two.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "slug": "engineering-team",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Team slug already exists for this department"
    }

    db_session.refresh(team_two)

    assert team_two.slug == "product-team"

def test_create_team_rejects_without_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-create-no-permission",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-create-no-permission-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-create-no-permission-branch",
    )

    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-create-no-permission-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="team.create.no.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="No Permission User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.create.no.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        f"/api/v1/teams/departments/{department.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "department_id": department.id,
            "name": "Unauthorized Team",
            "slug": "unauthorized-team",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}

    team = db_session.scalar(
        select(Team).where(Team.slug == "unauthorized-team")
    )

    assert team is None

def test_update_team_rejects_without_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-update-no-permission",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-update-no-permission-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-update-no-permission-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-update-no-permission-department",
    )
    db_session.add(department)
    db_session.flush()

    team = Team(
        department_id=department.id,
        name="Original Team Name",
        slug="original-team-slug",
    )
    db_session.add(team)

    user = User(
        organization_id=organization.id,
        email="team.update.no.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="No Permission User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.update.no.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/teams/{team.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Unauthorized Update",
            "slug": "unauthorized-update",
            "is_active": False,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}

    db_session.refresh(team)

    assert team.name == "Original Team Name"
    assert team.slug == "original-team-slug"
    assert team.is_active is True

def test_list_teams_rejects_without_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-list-no-permission",
    )

    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-list-no-permission-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-list-no-permission-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-list-no-permission-department",
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
        email="team.list.no.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="No Permission User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.list.no.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/teams/departments/{department.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}

def test_update_team_can_deactivate_team(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-deactivate",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-deactivate-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-deactivate-branch",
    )

    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-deactivate-department",
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
        email="team.deactivate@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Team Updater",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="TEAM_UPDATE",
        description="Update teams",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Team Updater",
        description="Can update teams",
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
            "email": "team.deactivate@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/teams/{team.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    db_session.refresh(team)

    assert team.is_active is False

def test_get_team_rejects_without_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="team-get-no-permission",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Current Organization Region",
        slug="team-get-no-permission-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Organization Branch",
        slug="team-get-no-permission-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Current Organization Department",
        slug="team-get-no-permission-department",
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
        email="team.get.no.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="No Permission User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "team.get.no.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/teams/{team.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}
