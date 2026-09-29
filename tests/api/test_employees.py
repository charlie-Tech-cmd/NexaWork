import pytest

from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
from app.models.region import Region
from app.models.user import User
from sqlalchemy import select


def test_get_employee_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="employee-api-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="employee-api-b",
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

    user_b = User(
        organization_id=organization_b.id,
        email="employee.api.b@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization B Employee",
        is_active=True,
    )
    user_a = User(
        organization_id=organization_a.id,
        email="employee.api.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_VIEW",
        description="View employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Employee Viewer",
        description="Can view employees",
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

    employee_b = Employee(
        organization_id=organization_b.id,
        user_id=user_b.id,
        employee_id="EMP-B-001",
        branch_id=branch_b.id,
        department_id=department_b.id,
        job_title="Developer",
    )

    db_session.add(employee_b)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/employees/{employee_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee not found"}


def test_create_employee_assigns_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Employee Create Organization",
        slug="employee-create-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Employee Create Region",
        slug="employee-create-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Employee Create Branch",
        slug="employee-create-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Employee Create Department",
        slug="employee-create-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee.create.success@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Employee Create User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_CREATE",
        description="Create employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Creator",
        description="Can create employees",
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
            "email": "employee.create.success@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/employees",
        json={
            "user_id": user.id,
            "employee_id": "EMP-CREATE-001",
            "branch_id": branch.id,
            "department_id": department.id,
            "job_title": "Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 201

    created_employee = db_session.scalar(
        select(Employee).where(
            Employee.employee_id == "EMP-CREATE-001"
        )
    )

    assert created_employee is not None
    assert created_employee.organization_id == organization.id
    assert created_employee.user_id == user.id
    assert created_employee.branch_id == branch.id
    assert created_employee.department_id == department.id


def test_create_employee_rejects_inactive_region(
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
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Region Branch",
        slug="inactive-region-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Region Department",
        slug="inactive-region-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.region.employee@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Region Employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_CREATE",
        description="Create employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Creator",
        description="Can create employees",
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
            "email": "inactive.region.employee@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/employees",
        json={
            "user_id": user.id,
            "employee_id": "EMP-INACTIVE-REGION-001",
            "branch_id": branch.id,
            "department_id": department.id,
            "job_title": "Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}


def test_create_employee_rejects_inactive_branch(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Branch Organization",
        slug="inactive-branch-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Branch Region",
        slug="inactive-branch-region",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Branch",
        slug="inactive-branch",
        is_active=False,
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Branch Department",
        slug="inactive-branch-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.branch.employee@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Branch Employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_CREATE",
        description="Create employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Creator",
        description="Can create employees",
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
            "email": "inactive.branch.employee@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/employees",
        json={
            "user_id": user.id,
            "employee_id": "EMP-INACTIVE-BRANCH-001",
            "branch_id": branch.id,
            "department_id": department.id,
            "job_title": "Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}


def test_create_employee_rejects_inactive_department(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Department Organization",
        slug="inactive-department-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Department Region",
        slug="inactive-department-region",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Department Branch",
        slug="inactive-department-branch",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Department",
        slug="inactive-department",
        is_active=False,
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.department.employee@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Department Employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_CREATE",
        description="Create employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Creator",
        description="Can create employees",
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
            "email": "inactive.department.employee@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/employees",
        json={
            "user_id": user.id,
            "employee_id": "EMP-INACTIVE-DEPARTMENT-001",
            "branch_id": branch.id,
            "department_id": department.id,
            "job_title": "Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}


@pytest.mark.parametrize(
    "inactive_level",
    ["region", "branch"],
)
def test_get_employee_rejects_inactive_hierarchy(
    client,
    db_session,
    inactive_level,
):
    organization = Organization(
        name="Inactive Hierarchy Organization",
        slug=f"employee-inactive-{inactive_level}",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Hierarchy Region",
        slug=f"employee-inactive-region-{inactive_level}",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Hierarchy Branch",
        slug=f"employee-inactive-branch-{inactive_level}",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Hierarchy Department",
        slug=f"employee-inactive-department-{inactive_level}",
        is_active=True,
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email=f"employee.inactive.{inactive_level}@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Hierarchy User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_VIEW",
        description="View employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Viewer",
        description="Can view employees",
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

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id=f"EMP-INACTIVE-{inactive_level.upper()}",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Developer",
    )
    db_session.add(employee)
    db_session.flush()

    if inactive_level == "region":
        region.is_active = False
    else:
        branch.is_active = False

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"employee.inactive.{inactive_level}@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/employees/{employee.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee not found"}


def test_update_employee_rejects_inactive_region(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Update Region Organization",
        slug="inactive-update-region-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Update Region",
        slug="inactive-update-region",
        is_active=False,
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Update Branch",
        slug="inactive-update-branch",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Update Department",
        slug="inactive-update-department",
        is_active=True,
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.update.region@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Update Region User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-INACTIVE-UPDATE-REGION-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Updater",
        description="Can update employees",
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
            "email": "inactive.update.region@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee.id}",
        json={
            "job_title": "Senior Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee not found"}


def test_update_employee_rejects_inactive_department(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Update Department Organization",
        slug="inactive-update-department-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Update Department Region",
        slug="inactive-update-department-region",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Update Department Branch",
        slug="inactive-update-department-branch",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive Update Department",
        slug="inactive-update-department",
        is_active=False,
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.update.department@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Update Department User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-INACTIVE-UPDATE-DEPT-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Updater",
        description="Can update employees",
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
            "email": "inactive.update.department@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee.id}",
        json={
            "job_title": "Senior Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee not found"}


def test_get_employee_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="current-employee-organization",
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
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="current.employee@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization Employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_VIEW",
        description="View employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Viewer",
        description="Can view employees",
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

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-CURRENT-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Software Engineer",
    )

    db_session.add(employee)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "current.employee@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/employees/{employee.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == employee.id
    assert response_data["user_id"] == user.id
    assert response_data["employee_id"] == "EMP-CURRENT-001"
    assert response_data["branch_id"] == branch.id
    assert response_data["department_id"] == department.id
    assert response_data["job_title"] == "Software Engineer"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None


def test_list_department_employees_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="employee-list-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="employee-list-b",
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
        email="employee.list.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_VIEW",
        description="View employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Employee Viewer",
        description="Can view employees",
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
            "email": "employee.list.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/employees/departments/{department_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}


def test_create_employee_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="employee-create-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="employee-create-b",
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

    user_a = User(
        organization_id=organization_a.id,
        email="employee.create.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_CREATE",
        description="Create employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Employee Creator",
        description="Can create employees",
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
            "email": "employee.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/employees",
        json={
            "user_id": user_a.id,
            "employee_id": "UNAUTHORIZED-EMP-001",
            "branch_id": branch_b.id,
            "department_id": department_b.id,
            "job_title": "Unauthorized Employee",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}

    created_employee = db_session.scalar(
        select(Employee).where(
            Employee.employee_id == "UNAUTHORIZED-EMP-001"
        )
    )

    assert created_employee is None

def test_create_employee_rejects_user_without_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Employee Permission Organization",
        slug="employee-permission-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Employee Permission Region",
        slug="employee-permission-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Employee Permission Branch",
        slug="employee-permission-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Employee Permission Department",
        slug="employee-permission-department",
    )
    db_session.add(department)
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
        email="employee.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Employee Permission User",
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
            "email": "employee.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/employees",
        json={
            "user_id": user.id,
            "employee_id": "EMP-PERMISSION-001",
            "branch_id": branch.id,
            "department_id": department.id,
            "job_title": "Software Engineer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}


def test_update_employee_requires_permission(
    client,
    db_session,
):
    organization = Organization(
        name="Organization",
        slug="employee-update-permission",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Employee Update Permission Region",
        slug="employee-update-permission-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Employee Update Permission Branch",
        slug="employee-update-permission-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Employee Update Permission Department",
        slug="employee-update-permission-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee.update.permission@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Employee Update Permission User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-UPDATE-PERMISSION-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Developer",
    )

    db_session.add(employee)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee.update.permission@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee.id}",
        json={
            "job_title": "Senior Developer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied"}

    db_session.refresh(employee)
    assert employee.job_title == "Developer"


def test_update_employee_rejects_another_organization_branch(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="employee-update-branch-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="employee-update-branch-b",
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
    db_session.flush()

    branch_a = Branch(
        organization_id=organization_a.id,
        region_id=region_a.id,
        name="Organization A Branch",
        slug="organization-a-branch",
    )

    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Organization B Branch",
        slug="organization-b-branch",
    )

    db_session.add_all([branch_a, branch_b])
    db_session.flush()

    department_a = Department(
        branch_id=branch_a.id,
        name="Organization A Department",
        slug="organization-a-department",
    )

    db_session.add(department_a)
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="employee.update.branch.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A Employee",
        is_active=True,
    )

    db_session.add(user_a)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )

    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Employee Updater",
        description="Can update employees",
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

    employee_a = Employee(
        organization_id=organization_a.id,
        user_id=user_a.id,
        employee_id="EMP-UPDATE-BRANCH-001",
        branch_id=branch_a.id,
        department_id=department_a.id,
        job_title="Developer",
    )

    db_session.add(employee_a)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee.update.branch.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee_a.id}",
        json={
            "branch_id": branch_b.id,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}

    db_session.refresh(employee_a)

    assert employee_a.branch_id == branch_a.id
    assert employee_a.department_id == department_a.id


def test_update_employee_rejects_another_organization_department(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="employee-update-department-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="employee-update-department-b",
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
    db_session.flush()

    branch_a = Branch(
        organization_id=organization_a.id,
        region_id=region_a.id,
        name="Organization A Branch",
        slug="organization-a-branch",
    )

    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Organization B Branch",
        slug="organization-b-branch",
    )

    db_session.add_all([branch_a, branch_b])
    db_session.flush()

    department_a = Department(
        branch_id=branch_a.id,
        name="Organization A Department",
        slug="organization-a-department",
    )
    department_b = Department(
        branch_id=branch_b.id,
        name="Organization B Department",
        slug="organization-b-department",
    )
    db_session.add_all([department_a, department_b])
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="employee.update.department.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A Employee",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Employee Updater",
        description="Can update employees",
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

    employee_a = Employee(
        organization_id=organization_a.id,
        user_id=user_a.id,
        employee_id="EMP-UPDATE-DEPARTMENT-001",
        branch_id=branch_a.id,
        department_id=department_a.id,
        job_title="Developer",
    )
    db_session.add(employee_a)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee.update.department.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee_a.id}",
        json={
            "department_id": department_b.id,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}

    db_session.refresh(employee_a)

    assert employee_a.branch_id == branch_a.id
    assert employee_a.department_id == department_a.id


def test_list_department_employees_excludes_employee_from_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="employee-list-direct-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="employee-list-direct-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    region_a = Region(
        organization_id=organization_a.id,
        name="Organization A Region",
        slug="employee-list-direct-region-a",
    )
    region_b = Region(
        organization_id=organization_b.id,
        name="Organization B Region",
        slug="employee-list-direct-region-b",
    )
    db_session.add_all([region_a, region_b])
    db_session.flush()

    branch_a = Branch(
        organization_id=organization_a.id,
        region_id=region_a.id,
        name="Organization A Branch",
        slug="employee-list-direct-branch-a",
    )
    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Organization B Branch",
        slug="employee-list-direct-branch-b",
    )
    db_session.add_all([branch_a, branch_b])
    db_session.flush()

    department_a = Department(
        branch_id=branch_a.id,
        name="Organization A Department",
        slug="employee-list-direct-department-a",
    )
    db_session.add(department_a)
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="employee.list.direct.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    user_b = User(
        organization_id=organization_b.id,
        email="employee.list.direct.b@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization B User",
        is_active=True,
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_VIEW",
        description="View employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization_a.id,
        name="Employee Viewer",
        description="Can view employees",
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

    employee_a = Employee(
        organization_id=organization_a.id,
        user_id=user_a.id,
        employee_id="EMP-LIST-DIRECT-A",
        branch_id=branch_a.id,
        department_id=department_a.id,
        job_title="Developer",
    )

    employee_b = Employee(
        organization_id=organization_b.id,
        user_id=user_b.id,
        employee_id="EMP-LIST-DIRECT-B",
        branch_id=branch_a.id,
        department_id=department_a.id,
        job_title="Developer",
    )

    db_session.add_all([employee_a, employee_b])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee.list.direct.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/employees/departments/{department_a.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert [employee["id"] for employee in response_data] == [employee_a.id]


@pytest.mark.parametrize(
    "inactive_level",
    ["region", "branch", "department"],
)
def test_list_department_employees_rejects_inactive_hierarchy(
    client,
    db_session,
    inactive_level,
):
    organization = Organization(
        name="Inactive List Hierarchy Organization",
        slug=f"employee-list-inactive-{inactive_level}",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive List Region",
        slug=f"employee-list-inactive-region-{inactive_level}",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive List Branch",
        slug=f"employee-list-inactive-branch-{inactive_level}",
        is_active=True,
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Inactive List Department",
        slug=f"employee-list-inactive-department-{inactive_level}",
        is_active=True,
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email=f"employee.list.inactive.{inactive_level}@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive List Hierarchy User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_VIEW",
        description="View employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Viewer",
        description="Can view employees",
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

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id=f"EMP-LIST-INACTIVE-{inactive_level.upper()}",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Developer",
    )
    db_session.add(employee)
    db_session.flush()

    if inactive_level == "region":
        region.is_active = False
    elif inactive_level == "branch":
        branch.is_active = False
    else:
        department.is_active = False

    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"employee.list.inactive.{inactive_level}@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/api/v1/employees/departments/{department.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}


def test_update_employee_rejects_inactive_target_branch(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Target Branch Organization",
        slug="inactive-target-branch-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Target Branch Region",
        slug="inactive-target-branch-region",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    current_branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Branch",
        slug="current-branch",
        is_active=True,
    )
    target_branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Target Branch",
        slug="inactive-target-branch",
        is_active=False,
    )
    db_session.add_all([current_branch, target_branch])
    db_session.flush()

    department = Department(
        branch_id=current_branch.id,
        name="Current Department",
        slug="current-department",
        is_active=True,
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.target.branch@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Target Branch User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-INACTIVE-TARGET-BRANCH-001",
        branch_id=current_branch.id,
        department_id=department.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Updater",
        description="Can update employees",
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
            "email": "inactive.target.branch@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee.id}",
        json={
            "branch_id": target_branch.id,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Branch not found"}


def test_update_employee_rejects_target_department_under_inactive_branch(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Department Branch Organization",
        slug="inactive-department-branch-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Department Branch Region",
        slug="inactive-department-branch-region",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    current_branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Branch",
        slug="current-department-current-branch",
        is_active=True,
    )
    target_branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Inactive Department Target Branch",
        slug="inactive-department-target-branch",
        is_active=False,
    )
    db_session.add_all([current_branch, target_branch])
    db_session.flush()

    current_department = Department(
        branch_id=current_branch.id,
        name="Current Department",
        slug="inactive-department-current-department",
        is_active=True,
    )
    target_department = Department(
        branch_id=target_branch.id,
        name="Target Department",
        slug="inactive-department-target-department",
        is_active=True,
    )
    db_session.add_all([current_department, target_department])
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.department.branch@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Department Branch User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-INACTIVE-DEPT-BRANCH-001",
        branch_id=current_branch.id,
        department_id=current_department.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Updater",
        description="Can update employees",
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
            "email": "inactive.department.branch@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee.id}",
        json={
            "department_id": target_department.id,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}


def test_update_employee_rejects_inactive_target_department(
    client,
    db_session,
):
    organization = Organization(
        name="Inactive Target Department Organization",
        slug="inactive-target-department-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Inactive Target Department Region",
        slug="inactive-target-department-region",
        is_active=True,
    )
    db_session.add(region)
    db_session.flush()

    current_branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Current Branch",
        slug="inactive-target-department-current-branch",
        is_active=True,
    )
    target_branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Target Branch",
        slug="inactive-target-department-target-branch",
        is_active=True,
    )
    db_session.add_all([current_branch, target_branch])
    db_session.flush()

    current_department = Department(
        branch_id=current_branch.id,
        name="Current Department",
        slug="inactive-target-department-current-department",
        is_active=True,
    )
    target_department = Department(
        branch_id=target_branch.id,
        name="Inactive Target Department",
        slug="inactive-target-department-target-department",
        is_active=False,
    )
    db_session.add_all([current_department, target_department])
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="inactive.target.department@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Inactive Target Department User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-INACTIVE-TARGET-DEPT-001",
        branch_id=current_branch.id,
        department_id=current_department.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.flush()

    permission = Permission(
        name="EMPLOYEE_UPDATE",
        description="Update employees",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Employee Updater",
        description="Can update employees",
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
            "email": "inactive.target.department@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.put(
        f"/api/v1/employees/{employee.id}",
        json={
            "branch_id": target_branch.id,
            "department_id": target_department.id,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}
