from fastapi import APIRouter, Depends, HTTPException, status
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
from app.models.organization import Organization
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.admin_employee_service import (
    create_employee as create_employee_service,
    get_employee as get_employee_service,
    list_department_employees as list_department_employees_service,
    update_employee as update_employee_service,
)

router = APIRouter(
    prefix="/api/v1/employees",
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
    try:
        return create_employee_service(
            db=db,
            organization_id=current_organization.id,
            user_id=employee.user_id,
            employee_id=employee.employee_id,
            branch_id=employee.branch_id,
            department_id=employee.department_id,
            job_title=employee.job_title,
            profile_picture=employee.profile_picture,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID or user is already assigned",
        )


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
    current_user: User = Depends(require_permission("EMPLOYEE_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return get_employee_service(
            db=db,
            organization_id=current_organization.id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

@router.get(
    "/departments/{department_id}",
    response_model=list[EmployeeResponse],
)
async def list_department_employees(
    department_id: int,
    current_user: User = Depends(require_permission("EMPLOYEE_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return list_department_employees_service(
            db=db,
            organization_id=current_organization.id,
            department_id=department_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: User = Depends(require_permission("EMPLOYEE_UPDATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return update_employee_service(
            db=db,
            organization_id=current_organization.id,
            employee_id=employee_id,
            employee_id_value=employee_data.employee_id,
            branch_id=employee_data.branch_id,
            department_id=employee_data.department_id,
            job_title=employee_data.job_title,
            profile_picture=employee_data.profile_picture,
            is_active=employee_data.is_active,
        )
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID or user is already assigned",
        )
