from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.department import Department
from app.models.region import Region


def create_department(
    db: Session,
    organization_id: int,
    branch_id: int,
    name: str,
    slug: str,
) -> Department:
    branch = db.scalar(
        select(Branch)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Branch.id == branch_id,
            Branch.is_active.is_(True),
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
        )
    )

    if branch is None:
        raise ValueError("Branch not found")

    new_department = Department(
        branch_id=branch_id,
        name=name,
        slug=slug,
    )

    db.add(new_department)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_department)
    return new_department


def get_department(
    db: Session,
    organization_id: int,
    department_id: int,
) -> Department:
    department = db.scalar(
        select(Department)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Department.id == department_id,
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
            Branch.is_active.is_(True),
        )
    )

    if department is None:
        raise ValueError("Department not found")

    return department


def list_branch_departments(
    db: Session,
    organization_id: int,
    branch_id: int,
) -> list[Department]:
    branch = db.scalar(
        select(Branch)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Branch.id == branch_id,
            Branch.is_active.is_(True),
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
        )
    )

    if branch is None:
        raise ValueError("Branch not found")

    return db.scalars(
        select(Department)
        .where(Department.branch_id == branch_id)
        .order_by(Department.id)
    ).all()


def update_department(
    db: Session,
    organization_id: int,
    department_id: int,
    name: str | None,
    slug: str | None,
    is_active: bool | None,
) -> Department:
    department = db.scalar(
        select(Department)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Department.id == department_id,
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
            Branch.is_active.is_(True),
        )
    )

    if department is None:
        raise ValueError("Department not found")

    if name is not None:
        department.name = name

    if slug is not None:
        department.slug = slug

    if is_active is not None:
        department.is_active = is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(department)
    return department
