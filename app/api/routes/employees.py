from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_employee,
    get_current_organization,
    get_current_user,
    require_permission,
)
from app.db.session import get_db
from app.models.employee import Employee
from app.models.branch import Branch
from app.models.department import Department
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)


router = APIRouter(
    prefix="/employees",
    tags=["employees"],
)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    employee: EmployeeCreate,
    current_user: User = Depends(require_permission("EMPLOYEE_CREATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):

    user = db.scalar(
        select(User).where(
            User.id == employee.user_id,
            User.organization_id == current_organization.id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    branch = db.scalar(
        select(Branch)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Branch.id == employee.branch_id,
            Region.organization_id == current_organization.id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    department = db.scalar(
        select(Department).where(
            Department.id == employee.department_id,
            Department.branch_id == branch.id,
        )
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    new_employee = Employee(
        user_id=employee.user_id,
        employee_id=employee.employee_id,
        branch_id=employee.branch_id,
        department_id=employee.department_id,
        job_title=employee.job_title,
        profile_picture=employee.profile_picture,
    )

    db.add(new_employee)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID or user is already assigned",
        )

    db.refresh(new_employee)

    return new_employee

@router.get(
    "/me",
    response_model=EmployeeResponse,
)
async def get_my_employee_profile(
    current_employee: Employee = Depends(get_current_employee),
):
    return current_employee

@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Employee.id == employee_id,
            Region.organization_id == current_organization.id,
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee

@router.get(
    "/departments/{department_id}",
    response_model=list[EmployeeResponse],
)
async def list_department_employees(
    department_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    department = db.scalar(
        select(Department)
        .join(Branch, Branch.id == Department.branch_id)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Department.id == department_id,
            Region.organization_id == current_organization.id,
        )
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    employees = db.scalars(
        select(Employee)
        .where(
            Employee.department_id == department_id
        )
        .order_by(Employee.id)
    ).all()

    return employees

@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee)
        .join(Branch, Branch.id == Employee.branch_id)
        .join(Region, Region.id == Branch.region_id)
        .where(
            Employee.id == employee_id,
            Region.organization_id == current_organization.id,
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if employee_data.branch_id is not None:
        branch = db.scalar(
            select(Branch)
            .join(Region, Region.id == Branch.region_id)
            .where(
                Branch.id == employee_data.branch_id,
                Region.organization_id == current_organization.id,
            )
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        employee.branch_id = employee_data.branch_id

    if employee_data.department_id is not None:
        target_branch_id = (
            employee_data.branch_id
            if employee_data.branch_id is not None
            else employee.branch_id
        )

        department = db.scalar(
            select(Department).where(
                Department.id == employee_data.department_id,
                Department.branch_id == target_branch_id,
            )
        )

        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found",
            )

        employee.department_id = employee_data.department_id

    if employee_data.employee_id is not None:
        employee.employee_id = employee_data.employee_id

    if employee_data.job_title is not None:
        employee.job_title = employee_data.job_title

    if employee_data.profile_picture is not None:
        employee.profile_picture = employee_data.profile_picture

    if employee_data.is_active is not None:
        employee.is_active = employee_data.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID or user is already assigned",
        )

    db.refresh(employee)

    return employee