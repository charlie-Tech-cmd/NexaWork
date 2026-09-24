from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.security.password import hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    AdminUserCreate,
    UserDeactivate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(require_permission("USER_CREATE")),
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(User.email == user_data.email)
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    new_user = User(
        organization_id=current_user.organization_id,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
    )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_permission("USER_UPDATE")),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_data.email is not None:
        existing_user = db.scalar(
            select(User).where(
                User.email == user_data.email,
                User.id != user_id,
            )
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user.email = user_data.email

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return user

@router.delete(
    "/{user_id}",
    response_model=UserResponse,
)
async def deactivate_user(
    user_id: int,
    user_data: UserDeactivate,
    current_user: User = Depends(require_permission("USER_DELETE")),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not verify_password(user_data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    user.is_active = False

    db.commit()
    db.refresh(user)

    return user

@router.get(
    "",
    response_model=list[UserResponse],
)
async def list_users(
    current_user: User = Depends(require_permission("USER_VIEW")),
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.id)
    ).all()

    return users


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("USER_VIEW")),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user