from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.api.dependencies import (
    get_current_organization,
    get_current_user,
)

from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import user_roles
from app.schemas.role import RoleResponse


router = APIRouter(
    prefix="/users",
    tags=["user-roles"],
)


@router.post(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_organization.id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

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

    existing_assignment = db.execute(
        select(user_roles).where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role_id,
        )
    ).first()

    if existing_assignment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role already assigned to user",
        )

    db.execute(
        user_roles.insert().values(
            user_id=user_id,
            role_id=role_id,
        )
    )

    db.commit()

@router.get(
    "/{user_id}/roles",
    response_model=list[RoleResponse],
)
async def list_user_roles(
    user_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_organization.id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    roles = db.scalars(
        select(Role)
        .join(
            user_roles,
            user_roles.c.role_id == Role.id,
        )
    .where(
        user_roles.c.user_id == user_id,
        Role.organization_id == current_organization.id,
    )
        ).all()

    return roles

@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_organization.id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

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

    existing_assignment = db.execute(
        select(user_roles).where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role_id,
        )
    ).first()

    if existing_assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role is not assigned to user",
        )

    db.execute(
        user_roles.delete().where(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role_id,
        )
    )

    db.commit()