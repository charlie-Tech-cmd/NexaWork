from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization, get_current_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services.department_service import (
    create_department as create_department_service,
    get_department as get_department_service,
    list_branch_departments as list_branch_departments_service,
    update_department as update_department_service,
)

router = APIRouter(
    prefix="/api/v1/departments",
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
    current_organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return create_department_service(
            db,
            current_organization.id,
            branch_id,
            department.name,
            department.slug,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department slug already exists for this branch",
        )


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
)
async def get_department(
    department_id: int,
    current_organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_department_service(
            db,
            current_organization.id,
            department_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/branches/{branch_id}",
    response_model=list[DepartmentResponse],
)
async def list_departments(
    branch_id: int,
    current_organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return list_branch_departments_service(
            db,
            current_organization.id,
            branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse,
)
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    current_organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_department_service(
            db,
            current_organization.id,
            department_id,
            department_data.name,
            department_data.slug,
            department_data.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department slug already exists for this branch",
        )
