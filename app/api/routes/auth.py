from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.api.dependencies import get_current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security.password import hash_password, verify_password
from app.core.security.jwt import create_access_token
from app.core.rate_limit import is_login_allowed
from app.db.session import get_db
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeLogin
from app.schemas.user import UserCreate, UserLogin, UserResponse

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
from app.schemas.user import AdminLogin

router = APIRouter(prefix="/api/v1")

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
    request: Request,
    user: UserLogin,
    db: Session = Depends(get_db),
):

    login_key = f"login:{request.client.host}:{user.email.lower()}"

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

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

@router.post("/auth/employee/login")
async def employee_login(
    request: Request,
    employee_login: EmployeeLogin,
    db: Session = Depends(get_db),
):

    login_key = (
        f"employee-login:{request.client.host}:"
        f"{employee_login.employee_id.lower()}"
    )

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    employee = db.scalar(
        select(Employee).where(
            Employee.employee_id == employee_login.employee_id,
            Employee.is_active.is_(True),
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    db_user = db.scalar(
        select(User).where(
            User.id == employee.user_id,
            User.is_active.is_(True),
        )
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    password_valid = verify_password(
        employee_login.password,
        db_user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee ID or password",
        )

    access_token = create_access_token(str(db_user.id))

    return {
        "message": "Login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "employee_id": employee.employee_id,
        "access_token": access_token,
    }

@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.post("/auth/admin/login")
async def admin_login(
    request: Request,
    admin_login: AdminLogin,
    db: Session = Depends(get_db),
):

    login_key = (
        f"admin-login:{request.client.host}:"
        f"{admin_login.email.lower()}"
    )

    if not is_login_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    db_user = db.scalar(
        select(User).where(
            User.email == admin_login.email,
            User.is_active.is_(True),
        )
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(
        admin_login.password,
        db_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    admin_role_exists = db.scalar(
        select(Role.id)
        .join(
            user_roles,
            user_roles.c.role_id == Role.id,
        )
        .join(
            role_permissions,
            role_permissions.c.role_id == Role.id,
        )
        .join(
            Permission,
            Permission.id == role_permissions.c.permission_id,
        )
        .where(
            user_roles.c.user_id == db_user.id,
            Role.organization_id == db_user.organization_id,
            Role.is_active.is_(True),
            Permission.name == "USER_CREATE",
            Permission.is_active.is_(True),
        )
    )

    if admin_role_exists is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    access_token = create_access_token(
        str(db_user.id),
        auth_type="admin",
    )

    return {
        "message": "Admin login successful",
        "id": db_user.id,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "access_token": access_token,
    }
