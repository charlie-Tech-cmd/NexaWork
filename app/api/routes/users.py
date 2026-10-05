from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.security.password import verify_password
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import (
    create_user as create_user_service,
    deactivate_user as deactivate_user_service,
    get_user as get_user_service,
    list_users as list_users_service,
    update_user as update_user_service,
)

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
    try:
        return create_user_service(
            db=db,
            organization_id=current_user.organization_id,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_permission("USER_UPDATE")),
    db: Session = Depends(get_db),
):
    try:
        return update_user_service(
            db=db,
            user_id=user_id,
            organization_id=current_user.organization_id,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
        )
    except ValueError as exc:
        if str(exc) == "Email already registered":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


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
    try:
        return deactivate_user_service(
            db=db,
            user_id=user_id,
            organization_id=current_user.organization_id,
            password=user_data.password,
            current_user_password_hash=current_user.password_hash,
        )
    except ValueError as exc:
        if str(exc) == "Invalid password":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[UserResponse],
)
async def list_users(
    current_user: User = Depends(require_permission("USER_VIEW")),
    db: Session = Depends(get_db),
):
    return list_users_service(
        db=db,
        organization_id=current_user.organization_id,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("USER_VIEW")),
    db: Session = Depends(get_db),
):
    try:
        return get_user_service(
            db=db,
            user_id=user_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc