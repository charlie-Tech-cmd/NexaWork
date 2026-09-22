from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.security.jwt import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
from app.models.organization import Organization
from app.models.employee import Employee


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    db_user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return db_user

def get_current_employee(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Employee:
    employee = db.scalar(
        select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required",
        )

    return employee


def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == current_user.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive or unavailable",
        )

    return organization


def require_permission(permission_name: str):
    def permission_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        permission_exists = db.scalar(
            select(Permission.id)
            .join(
                role_permissions,
                role_permissions.c.permission_id == Permission.id,
            )
            .join(
                user_roles,
                user_roles.c.role_id == role_permissions.c.role_id,
            )
            .join(
                Role,
                Role.id == user_roles.c.role_id,
            )
            .where(
                user_roles.c.user_id == current_user.id,
                Permission.name == permission_name,
                Permission.is_active.is_(True),
                Role.is_active.is_(True),
                Role.organization_id == current_user.organization_id,
            )
        )

        if permission_exists is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        return current_user

    return permission_dependency
