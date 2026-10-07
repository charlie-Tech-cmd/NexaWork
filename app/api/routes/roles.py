from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    require_any_permission,
    require_permission,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.permission import PermissionResponse
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.services.role_service import (
    assign_permission_to_role as assign_permission_to_role_service,
    create_role as create_role_service,
    delete_role as delete_role_service,
    get_role as get_role_service,
    list_role_permissions as list_role_permissions_service,
    list_roles as list_roles_service,
    remove_permission_from_role as remove_permission_from_role_service,
    update_role as update_role_service,
)

router = APIRouter(
    prefix="/api/v1/roles",
    tags=["roles"],
)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    role: RoleCreate,
    current_user: User = Depends(require_permission("ROLE_CREATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return create_role_service(
            db,
            current_organization.id,
            role.name,
            role.description,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role name already exists",
        )


@router.get(
    "",
    response_model=list[RoleResponse],
)
async def list_roles(
    current_user: User = Depends(require_permission("ROLE_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    return list_roles_service(
        db,
        current_organization.id,
    )


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
)
async def get_role(
    role_id: int,
    current_user: User = Depends(require_permission("ROLE_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return get_role_service(
            db,
            current_organization.id,
            role_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(require_permission("ROLE_UPDATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return update_role_service(
            db,
            current_organization.id,
            role_id,
            role_data.name,
            role_data.description,
            role_data.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role name already exists",
        )


@router.post(
    "/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(
        require_any_permission(
            "ROLE_ASSIGN_PERMISSION",
            "ROLE_UPDATE",
        )
    ),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        assign_permission_to_role_service(
            db,
            current_organization.id,
            role_id,
            permission_id,
        )
    except ValueError as exc:
        detail = str(exc)

        if detail == "Role not found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail == "Permission not found":
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )


@router.get(
    "/{role_id}/permissions",
    response_model=list[PermissionResponse],
)
async def list_role_permissions(
    role_id: int,
    current_user: User = Depends(require_permission("ROLE_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return list_role_permissions_service(
            db,
            current_organization.id,
            role_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_permission("ROLE_DELETE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        delete_role_service(
            db,
            current_organization.id,
            role_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(
        require_any_permission(
            "ROLE_REMOVE_PERMISSION",
            "ROLE_UPDATE",
        )
    ),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        remove_permission_from_role_service(
            db,
            current_organization.id,
            role_id,
            permission_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
