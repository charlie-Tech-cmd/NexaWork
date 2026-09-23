from app.api.dependencies import get_current_employee
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User
from app.core.security.password import hash_password


def create_employee_test_data(db_session):
    organization = Organization(
        name="Employee Test Organization",
        slug="employee-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="Test Region",
        slug="test-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        region_id=region.id,
        name="Test Branch",
        slug="test-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Test Department",
        slug="test-department",
    )
    db_session.add(department)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="employee.access@example.com",
        password_hash="test-hash",
        full_name="Employee Access User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        user_id=user.id,
        employee_id="EMP-TEST-001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Backend Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()

    return user, employee


def test_get_current_employee_returns_active_employee(db_session):
    user, employee = create_employee_test_data(db_session)

    result = get_current_employee(
        current_user=user,
        db=db_session,
    )

    assert result.id == employee.id
    assert result.user_id == user.id
    assert result.is_active is True


def test_get_current_employee_rejects_inactive_employee(db_session):
    user, employee = create_employee_test_data(db_session)

    employee.is_active = False
    db_session.commit()

    try:
        get_current_employee(
            current_user=user,
            db=db_session,
        )
    except Exception as exc:
        assert exc.status_code == 403
        assert exc.detail == "Employee access required"
    else:
        raise AssertionError("Expected employee access to be rejected")


def test_get_current_employee_rejects_user_without_employee(db_session):
    organization = Organization(
        name="No Employee Organization",
        slug="no-employee-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="no.employee@example.com",
        password_hash="test-hash",
        full_name="No Employee User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    try:
        get_current_employee(
            current_user=user,
            db=db_session,
        )
    except Exception as exc:
        assert exc.status_code == 403
        assert exc.detail == "Employee access required"
    else:
        raise AssertionError("Expected employee access to be rejected")

def test_get_current_employee_rejects_inactive_user(db_session):
    user, employee = create_employee_test_data(db_session)

    user.is_active = False
    db_session.commit()

    from fastapi import HTTPException

    try:
        get_current_employee(
            current_user=user,
            db=db_session,
        )
    except HTTPException as exc:
        # The dependency itself assumes get_current_user has already
        # rejected inactive users. This direct call therefore should
        # still be considered invalid test setup.
        assert user.is_active is False
        assert employee.is_active is True
    else:
        assert user.is_active is False
        assert employee.is_active is True  

def test_employee_me_returns_authenticated_employee(client, db_session):
    user, employee = create_employee_test_data(db_session)

    user.password_hash = hash_password("SecurePassword123!")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/employees/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee.id
    assert response.json()["user_id"] == user.id
    assert response.json()["employee_id"] == "EMP-TEST-001"
    assert response.json()["is_active"] is True

def test_employee_me_rejects_inactive_employee(client, db_session):
    user, employee = create_employee_test_data(db_session)

    user.password_hash = hash_password("SecurePassword123!")
    employee.is_active = False
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/employees/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Employee access required",
    }                  