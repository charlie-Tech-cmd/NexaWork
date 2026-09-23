from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User


def create_employee_login_test_data(db_session):
    organization = Organization(
        name="Employee Login Organization",
        slug="employee-login-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Login Region",
        slug="login-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        region_id=region.id,
        name="Login Branch",
        slug="login-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Login Department",
        slug="login-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee.login@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Employee Login User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        user_id=user.id,
        employee_id="EMP-LOGIN-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Backend Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()

    return user, employee


def test_employee_login_returns_access_token(client, db_session):
    user, employee = create_employee_login_test_data(db_session)

    response = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": employee.employee_id,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Login successful"
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert data["full_name"] == user.full_name
    assert data["employee_id"] == employee.employee_id
    assert data["access_token"]


def test_employee_login_rejects_wrong_password(client, db_session):
    _, employee = create_employee_login_test_data(db_session)

    response = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": employee.employee_id,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid employee ID or password",
    }


def test_employee_login_rejects_unknown_employee_id(client, db_session):
    create_employee_login_test_data(db_session)

    response = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": "EMP-UNKNOWN-999",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid employee ID or password",
    }


def test_employee_login_rejects_inactive_employee(client, db_session):
    _, employee = create_employee_login_test_data(db_session)

    employee.is_active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": employee.employee_id,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid employee ID or password",
    }


def test_employee_login_rejects_inactive_user(client, db_session):
    user, employee = create_employee_login_test_data(db_session)

    user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": employee.employee_id,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid employee ID or password",
    }


def test_employee_login_token_accesses_employee_profile(
    client,
    db_session,
):
    _, employee = create_employee_login_test_data(db_session)

    login_response = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": employee.employee_id,
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/employees/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == employee.employee_id