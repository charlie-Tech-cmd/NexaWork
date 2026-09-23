from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization, get_current_user
from app.core.security.password import hash_password
from app.db.session import get_db
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user_role import user_roles
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOnboardingCreate,
    OrganizationOnboardingResponse,
    OrganizationResponse,
)


router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["organizations"],
)

@router.post(
    "/onboard",
    response_model=OrganizationOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def onboard_organization(
    onboarding: OrganizationOnboardingCreate,
    db: Session = Depends(get_db),
):
    existing_organization = db.scalar(
        select(Organization).where(
            Organization.slug == onboarding.organization_slug,
        )
    )

    if existing_organization is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )

    existing_user = db.scalar(
        select(User).where(
            User.email == onboarding.admin_email,
        )
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    new_organization = Organization(
        name=onboarding.organization_name,
        slug=onboarding.organization_slug,
    )
    db.add(new_organization)
    db.flush()

    new_admin = User(
        organization_id=new_organization.id,
        email=onboarding.admin_email,
        password_hash=hash_password(onboarding.admin_password),
        full_name=onboarding.admin_full_name,
        is_active=True,
    )
    db.add(new_admin)
    db.flush()

    admin_role = Role(
        organization_id=new_organization.id,
        name="Organization Admin",
        description="Manage users and organization-level administration",
        is_active=True,
    )
    db.add(admin_role)
    db.flush()

    permissions = db.scalars(
        select(Permission).where(
            Permission.name.in_(
                [
                    "USER_VIEW",
                    "USER_CREATE",
                    "USER_UPDATE",
                    "USER_DELETE",
                ]
            ),
            Permission.is_active.is_(True),
        )
    ).all()

    if len(permissions) != 4:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Required permissions are not configured",
        )

    for permission in permissions:
        db.execute(
            role_permissions.insert().values(
                role_id=admin_role.id,
                permission_id=permission.id,
            )
        )

    db.execute(
        user_roles.insert().values(
            user_id=new_admin.id,
            role_id=admin_role.id,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization or administrator already exists",
        )

    db.refresh(new_organization)
    db.refresh(new_admin)

    return {
        "organization": new_organization,
        "admin": new_admin,
    }


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    organization: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_organization = Organization(
        name=organization.name,
        slug=organization.slug,
    )

    db.add(new_organization)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )

    db.refresh(new_organization)

    return new_organization


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
async def get_organization(
    organization_id: int,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.id == current_organization.id,
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization
