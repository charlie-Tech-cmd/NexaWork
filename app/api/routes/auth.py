from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies import get_current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security.password import hash_password, verify_password
from app.core.security.jwt import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse

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

@router.post("/auth/login")
async def login_user(
    user: UserLogin,
    db: Session = Depends(get_db),
):
    db_user = db.scalar(
        select(User).where(User.email == user.email)
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    password_valid = verify_password(
        user.password,
        db_user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(str(db_user.id))

    return {
        "message": "Login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "access_token": access_token,
    }

@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user
