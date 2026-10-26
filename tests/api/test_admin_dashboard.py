from app.core.security.password import hash_password

from app.models.branch import Branch
from app.models.department import Department
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.region import Region
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def test_admin_dashboard_department_count_is_organization_scoped(
    client,
    db_session,
):
    organization_a = Organization(
        name="Dashboard Organization A",
        slug="dashboard-organization-a",
    )
    organization_b = Organization(
        name="Dashboard Organization B",
        slug="dashboard-organization-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    region_a = Region(
        organization_id=organization_a.id,
        name="Dashboard Region A",
        slug="dashboard-region-a",
    )
    region_b = Region(
        organization_id=organization_b.id,
        name="Dashboard Region B",
        slug="dashboard-region-b",
    )
    db_session.add_all([region_a, region_b])
    db_session.flush()

    branch_a = Branch(
        organization_id=organization_a.id,
        region_id=region_a.id,
        name="Dashboard Branch A",
        slug="dashboard-branch-a",
    )
    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Dashboard Branch B",
        slug="dashboard-branch-b",
    )
    db_session.add_all([branch_a, branch_b])
    db_session.flush()

    db_session.add_all([
        Department(
            branch_id=branch_a.id,
            name="Dashboard Department A",
            slug="dashboard-department-a",
        ),
        Department(
            branch_id=branch_b.id,
            name="Dashboard Department B",
            slug="dashboard-department-b",
        ),
    ])

    permission = Permission(
        name="ADMIN_ACCESS",
        description="Access administrative portal",
        is_active=True,
    )
    role = Role(
        organization_id=organization_a.id,
        name="Dashboard Admin",
        description="Dashboard test admin role",
        is_active=True,
    )
    user = User(
        organization_id=organization_a.id,
        email="dashboard.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Dashboard Test Admin",
        is_active=True,
    )
    db_session.add_all([permission, role, user])
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

    login = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )
    assert login.status_code == 200, login.text

    response = client.get(
        "/api/v1/admin/dashboard",
        headers={
            "Authorization": f"Bearer {login.json()['access_token']}",
        },
    )

    assert response.status_code == 200, response.text
    dashboard = response.json()
    assert dashboard["organization_id"] == organization_a.id
    assert dashboard["total_branches"] == 1
    assert dashboard["total_departments"] == 1
