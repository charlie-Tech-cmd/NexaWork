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
        organization_id=organization.id,
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
        password_hash=hash_password("SecurePassword123!"),
        full_name="Employee Access User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
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


def test_get_current_employee_rejects_mismatched_organization(db_session):
    organization_a = Organization(
        name="Employee Access Organization A",
        slug="employee-access-organization-a",
    )
    organization_b = Organization(
        name="Employee Access Organization B",
        slug="employee-access-organization-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    region_b = Region(
        organization_id=organization_b.id,
        name="Employee Access Region B",
        slug="employee-access-region-b",
    )
    db_session.add(region_b)
    db_session.flush()

    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Employee Access Branch B",
        slug="employee-access-branch-b",
    )
    db_session.add(branch_b)
    db_session.flush()

    department_b = Department(
        branch_id=branch_b.id,
        name="Employee Access Department B",
        slug="employee-access-department-b",
    )
    db_session.add(department_b)
    db_session.flush()

    user = User(
        organization_id=organization_a.id,
        email="employee.mismatch@example.com",
        password_hash="test-hash",
        full_name="Employee Mismatch User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    employee = Employee(
        organization_id=organization_b.id,
        user_id=user.id,
        employee_id="EMP-MISMATCH-001",
        branch_id=branch_b.id,
        department_id=department_b.id,
        job_title="Developer",
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()

    try:
        get_current_employee(current_user=user, db=db_session)
    except Exception as exc:
        assert exc.status_code == 403
        assert exc.detail == "Employee access required"
    else:
        raise AssertionError("Expected employee access to be rejected")
