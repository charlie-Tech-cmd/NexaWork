from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.employee import Employee
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    "/{employee_id}",
    response_model=EmployeeResponse,
)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


@router.get(
    "/branches/{branch_id}",
    response_model=list[EmployeeResponse],
)
async def list_branch_employees(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employees = db.scalars(
        select(Employee)
        .where(
            Employee.branch_id == branch_id
        )
        .order_by(Employee.id)
    ).all()

    return employees


@router.get(
    "/departments/{department_id}",
    response_model=list[EmployeeResponse],
)
async def list_department_employees(
    department_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if employee_data.employee_id is not None:
        employee.employee_id = employee_data.employee_id

    if employee_data.branch_id is not None:
        employee.branch_id = employee_data.branch_id

    if employee_data.department_id is not None:
        employee.department_id = employee_data.department_id

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