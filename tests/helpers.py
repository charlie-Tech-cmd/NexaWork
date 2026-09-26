from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User


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