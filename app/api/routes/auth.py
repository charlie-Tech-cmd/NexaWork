from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate


router = APIRouter()


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    password_hash = hash_password(user.password)

    new_user = User(
        email=user.email,
        password_hash=password_hash,
        full_name=user.full_name,
    )

    db.add(new_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
    }
