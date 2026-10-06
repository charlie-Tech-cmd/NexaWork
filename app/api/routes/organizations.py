from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


from app.api.dependencies import (
    get_current_organization,
    get_current_super_admin,
    get_current_user,
    require_permission,
)

from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOnboardingCreate,
    OrganizationOnboardingResponse,
    OrganizationResponse,
    OrganizationStatusUpdate,
    OrganizationUpdate,
)
from app.services.organization_service import (
    create_organization as create_organization_service,
    get_organization as get_organization_service,
    onboard_organization as onboard_organization_service,
    update_organization as update_organization_service,
    update_organization_status as update_organization_status_service,
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
    try:
        return onboard_organization_service(
            db=db,
            organization_name=onboarding.organization_name,
            organization_slug=onboarding.organization_slug,
            admin_email=onboarding.admin_email,
            admin_password=onboarding.admin_password,
            admin_full_name=onboarding.admin_full_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization or administrator already exists",
        )

@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    organization: OrganizationCreate,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    try:
        return create_organization_service(
            db=db,
            name=organization.name,
            slug=organization.slug,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )


@router.patch(
    "/{organization_id}/status",
    response_model=OrganizationResponse,
)
async def update_organization_status(
    organization_id: int,
    status_update: OrganizationStatusUpdate,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    try:
        return update_organization_status_service(
            db=db,
            organization_id=organization_id,
            is_active=status_update.is_active,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )


@router.get(
    "/me",
    response_model=OrganizationResponse,
)
async def get_my_organization(
    current_organization: Organization = Depends(get_current_organization),
):
    return current_organization


@router.patch(
    "/me",
    response_model=OrganizationResponse,
)
async def update_my_organization(
    organization_update: OrganizationUpdate,
    current_organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(
        require_permission("ORGANIZATION_UPDATE")
    ),
    db: Session = Depends(get_db),
):
    try:
        return update_organization_service(
            db=db,
            organization=current_organization,
            name=organization_update.name,
            slug=organization_update.slug,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
async def get_organization(
    organization_id: int,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return get_organization_service(
            db=db,
            organization_id=organization_id,
            current_organization_id=current_organization.id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
