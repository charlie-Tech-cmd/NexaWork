from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.employee import Employee
from app.models.branch import Branch
from app.models.department import Department
from app.models.user import User


def get_admin_dashboard_overview(
    db: Session,
    organization_id: int,
):
    total_employees = db.scalar(
        select(func.count(Employee.id))
        .where(
            Employee.organization_id == organization_id
        )
    )

    active_employees = db.scalar(
        select(func.count(Employee.id))
        .where(
            Employee.organization_id == organization_id,
            Employee.is_active.is_(True),
        )
    )

    total_branches = db.scalar(
        select(func.count(Branch.id))
        .where(
            Branch.organization_id == organization_id
        )
    )

    total_departments = db.scalar(
        select(func.count(Department.id))
        .where(
            Department.organization_id == organization_id
        )
    )

    total_users = db.scalar(
        select(func.count(User.id))
        .where(
            User.organization_id == organization_id
        )
    )

    return {
        "organization_id": organization_id,
        "total_employees": total_employees or 0,
        "active_employees": active_employees or 0,
        "total_branches": total_branches or 0,
        "total_departments": total_departments or 0,
        "total_users": total_users or 0,
    }
