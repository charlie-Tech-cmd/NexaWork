from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.organization import Organization
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

    employee_b = Employee(
        user_id=user_b.id,
        employee_id="EMP-B-001",
        branch_id=branch_b.id,
        department_id=department_b.id,
        job_title="Developer",
    )
    db_session.add(employee_b)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "employee.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/employees/{employee_b.id}",
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

    employee = Employee(
        user_id=user.id,
        employee_id="EMP-CURRENT-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Software Engineer",
    )
    db_session.add(employee)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "current.employee@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/employees/{employee.id}",
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
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "employee.list.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/employees/departments/{department_b.id}",
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
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "employee.create.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/employees",
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