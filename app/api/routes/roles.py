from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    get_current_user,
)

from app.db.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.organization import Organization
from app.models.user import User
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.schemas.permission import PermissionResponse

router = APIRouter(
    prefix="/roles",
    tags=["roles"],
)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    role: RoleCreate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):

    new_role = Role(
        organization_id=current_organization.id,
        name=role.name,
        description=role.description,
    )

    db.add(new_role)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role name already exists",
        )

    db.refresh(new_role)

    return new_role

@router.get(
    "",
    response_model=list[RoleResponse],
)
async def list_roles(
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    roles = db.scalars(
        select(Role)
        .where(Role.organization_id == current_organization.id)
        .order_by(Role.id)
    ).all()

    return roles

@router.get(
    "/{role_id}",
    response_model=RoleResponse,
)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_organization.id,
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return role

@router.put(
    "/{role_id}",
    response_model=RoleResponse,
)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_organization.id,
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role_data.name is not None:
        role.name = role_data.name

    if role_data.description is not None:
        role.description = role_data.description

    if role_data.is_active is not None:
        role.is_active = role_data.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role name already exists",
        )

    db.refresh(role)

    return role

@router.post(
    "/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_organization.id,
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    permission = db.get(Permission, permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    existing_assignment = db.execute(
        select(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    ).first()

    if existing_assignment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission already assigned to role",
        )

    db.execute(
        role_permissions.insert().values(
            role_id=role_id,
            permission_id=permission_id,
        )
    )

    db.commit()

@router.get(
    "/{role_id}/permissions",
    response_model=list[PermissionResponse],
)
async def list_role_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_organization.id,
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    permissions = db.scalars(
        select(Permission)
        .join(
            role_permissions,
            role_permissions.c.permission_id == Permission.id,
        )
        .where(role_permissions.c.role_id == role_id)
        .order_by(Permission.id)
    ).all()

    return permissions

@router.delete(
    "/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):

    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == current_organization.id,
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    permission = db.get(Permission, permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    existing_assignment = db.execute(
        select(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    ).first()

    if existing_assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission is not assigned to role",
        )

    db.execute(
        role_permissions.delete().where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    )

    db.commit()
