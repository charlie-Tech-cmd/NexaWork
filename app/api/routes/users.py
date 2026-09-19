from fastapi import APIRouter, Depends
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
