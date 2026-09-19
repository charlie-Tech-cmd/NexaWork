from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get(
    "",
    response_model=list[UserResponse],
)
async def list_users(
    current_user: User = Depends(require_permission("USER_VIEW")),
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(User).order_by(User.id)
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
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user