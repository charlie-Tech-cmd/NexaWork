from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization, get_current_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.region import (
    RegionCreate,
    RegionResponse,
    RegionUpdate,
)
from app.services.region_service import (
    create_region as create_region_service,
    get_region as get_region_service,
    list_regions as list_regions_service,
    update_region as update_region_service,
)

router = APIRouter(
    prefix="/api/v1/regions",
    tags=["regions"],
)


@router.post(
    "/organizations/{organization_id}",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_region(
    organization_id: int,
    region: RegionCreate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    if organization_id != current_organization.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    try:
        return create_region_service(
            db,
            current_organization.id,
            region.name,
            region.slug,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Region slug already exists for this organization",
        )


@router.get(
    "/{region_id}",
    response_model=RegionResponse,
)
async def get_region(
    region_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return get_region_service(
            db,
            current_organization.id,
            region_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/organizations/{organization_id}",
    response_model=list[RegionResponse],
)
async def list_regions(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    if organization_id != current_organization.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return list_regions_service(
        db,
        current_organization.id,
    )


@router.put(
    "/{region_id}",
    response_model=RegionResponse,
)
async def update_region(
    region_id: int,
    region_data: RegionUpdate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return update_region_service(
            db,
            current_organization.id,
            region_id,
            region_data.name,
            region_data.slug,
            region_data.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Region slug already exists for this organization",
        )
