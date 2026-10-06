from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.region import Region
from app.models.user import User


def create_employee(
    db: Session,
    organization_id: int,
    user_id: int,
    employee_id: str,
    branch_id: int,
    department_id: int,
    job_title: str,
    profile_picture: str | None,
) -> Employee:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise ValueError("User not found")

    branch = db.scalar(
        select(Branch)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Branch.id == branch_id,
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
            Branch.is_active.is_(True),
        )
    )

    if branch is None:
        raise ValueError("Branch not found")

    department = db.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.branch_id == branch.id,
            Department.is_active.is_(True),
        )
    )

    if department is None:
        raise ValueError("Department not found")

    new_employee = Employee(
        organization_id=organization_id,
        user_id=user_id,
        employee_id=employee_id,
        branch_id=branch_id,
        department_id=department_id,
        job_title=job_title,
        profile_picture=profile_picture,
    )

    db.add(new_employee)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_employee)

    return new_employee


def get_employee(
    db: Session,
    organization_id: int,
    employee_id: int,
) -> Employee:
    employee = db.scalar(
        select(Employee)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Employee.id == employee_id,
            Employee.organization_id == organization_id,
            Employee.is_active.is_(True),
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
            Branch.is_active.is_(True),
        )
    )

    if employee is None:
        raise ValueError("Employee not found")

    return employee
