from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.schemas.permission import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)


router = APIRouter(
    prefix="/api/v1/permissions",
    tags=["permissions"],
)


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("PERMISSION_CREATE")
    ),
):
    new_permission = Permission(
        name=permission.name,
        description=permission.description,
    )

    db.add(new_permission)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission name already exists",
        )

    db.refresh(new_permission)

    return new_permission


@router.get(
    "",
    response_model=list[PermissionResponse],
)
async def list_permissions(
    current_user: User = Depends(
        require_permission("PERMISSION_VIEW")
    ),
    db: Session = Depends(get_db),
):
    permissions = db.scalars(
        select(Permission).order_by(Permission.id)
    ).all()

    return permissions


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
)
async def get_permission(
    permission_id: int,
    current_user: User = Depends(
        require_permission("PERMISSION_VIEW")
    ),
    db: Session = Depends(get_db),
):
    permission = db.get(Permission, permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    return permission


@router.put(
    "/{permission_id}",
    response_model=PermissionResponse,
)
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    current_user: User = Depends(
        require_permission("PERMISSION_UPDATE")
    ),    db: Session = Depends(get_db),
):
    permission = db.get(Permission, permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    if permission_data.name is not None:
        permission.name = permission_data.name

    if permission_data.description is not None:
        permission.description = permission_data.description

    if permission_data.is_active is not None:
        permission.is_active = permission_data.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission name already exists",
        )

    db.refresh(permission)

    return permission

@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_permission(
    permission_id: int,
    current_user: User = Depends(
        require_permission("PERMISSION_DELETE")
    ),
    db: Session = Depends(get_db),
):
    permission = db.get(Permission, permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    db.delete(permission)
    db.commit()

    return None    