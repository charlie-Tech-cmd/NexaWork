import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User


def _create_hierarchy(session: Session):
    """Create two valid organizations and their related hierarchy records."""
    organization_a = Organization(
        name="Constraint Organization A",
        slug="constraint-organization-a",
    )
    organization_b = Organization(
        name="Constraint Organization B",
        slug="constraint-organization-b",
    )
    session.add_all([organization_a, organization_b])
    session.flush()

    region_a = Region(
        organization_id=organization_a.id,
        name="Region A",
        slug="region-a",
    )
    region_b = Region(
        organization_id=organization_b.id,
        name="Region B",
        slug="region-b",
    )
    session.add_all([region_a, region_b])
    session.flush()

    branch_a = Branch(
        organization_id=organization_a.id,
        region_id=region_a.id,
        name="Branch A",
        slug="branch-a",
    )
    branch_b = Branch(
        organization_id=organization_b.id,
        region_id=region_b.id,
        name="Branch B",
        slug="branch-b",
    )
    session.add_all([branch_a, branch_b])
    session.flush()

    department_a = Department(
        branch_id=branch_a.id,
        name="Department A",
        slug="department-a",
    )
    department_b = Department(
        branch_id=branch_b.id,
        name="Department B",
        slug="department-b",
    )
    session.add_all([department_a, department_b])
    session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="constraint-user-a@example.com",
        password_hash="test-hash",
        full_name="Constraint User A",
        is_active=True,
    )
    session.add(user_a)
    session.flush()

    return {
        "organization_a": organization_a,
        "organization_b": organization_b,
        "region_a": region_a,
        "region_b": region_b,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "department_a": department_a,
        "department_b": department_b,
        "user_a": user_a,
    }


def _create_test_session():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_database_rejects_branch_region_organization_mismatch():
    engine, session = _create_test_session()

    try:
        records = _create_hierarchy(session)
        session.commit()

        invalid_branch = Branch(
            organization_id=records["organization_a"].id,
            region_id=records["region_b"].id,
            name="Invalid Branch",
            slug="invalid-branch",
        )
        session.add(invalid_branch)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_employee_branch_organization_mismatch():
    engine, session = _create_test_session()

    try:
        records = _create_hierarchy(session)
        session.commit()

        invalid_employee = Employee(
            organization_id=records["organization_a"].id,
            user_id=records["user_a"].id,
            employee_id="INVALID-ORG-BRANCH",
            branch_id=records["branch_b"].id,
            department_id=records["department_b"].id,
            job_title="Test Employee",
            is_active=True,
        )
        session.add(invalid_employee)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_employee_department_branch_mismatch():
    engine, session = _create_test_session()

    try:
        records = _create_hierarchy(session)
        session.commit()

        invalid_employee = Employee(
            organization_id=records["organization_a"].id,
            user_id=records["user_a"].id,
            employee_id="INVALID-DEPARTMENT-BRANCH",
            branch_id=records["branch_a"].id,
            department_id=records["department_b"].id,
            job_title="Test Employee",
            is_active=True,
        )
        session.add(invalid_employee)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_employee_user_organization_mismatch():
    engine, session = _create_test_session()

    try:
        records = _create_hierarchy(session)

        user_b = User(
            organization_id=records["organization_b"].id,
            email="constraint-user-b@example.com",
            password_hash="test-hash",
            full_name="Constraint User B",
            is_active=True,
        )
        session.add(user_b)
        session.commit()

        invalid_employee = Employee(
            organization_id=records["organization_a"].id,
            user_id=user_b.id,
            employee_id="INVALID-USER-ORG",
            branch_id=records["branch_a"].id,
            department_id=records["department_a"].id,
            job_title="Test Employee",
            is_active=True,
        )
        session.add(invalid_employee)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()
    finally:
        session.close()
        engine.dispose()
