from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)


router = APIRouter(
    prefix="/departments",
    tags=["departments"],
)


@router.post(
    "/branches/{branch_id}",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    branch_id: int,
    department: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_department = Department(
        branch_id=branch_id,
        name=department.name,
        slug=department.slug,
    )

    db.add(new_department)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department slug already exists for this branch",
        )

    db.refresh(new_department)

    return new_department


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
)
async def get_department(
    department_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    department = db.scalar(
        select(Department).where(
            Department.id == department_id
        )
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    return department


@router.get(
    "/branches/{branch_id}",
    response_model=list[DepartmentResponse],
)
async def list_departments(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    departments = db.scalars(
        select(Department)
        .where(
            Department.branch_id == branch_id
        )
        .order_by(Department.id)
    ).all()

    return departments


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse,
)
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    department = db.scalar(
        select(Department).where(
            Department.id == department_id
        )
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    if department_data.name is not None:
        department.name = department_data.name

    if department_data.slug is not None:
        department.slug = department_data.slug

    if department_data.is_active is not None:
        department.is_active = department_data.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department slug already exists for this branch",
        )

    db.refresh(department)

    return department