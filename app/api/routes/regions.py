from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.region import Region
from app.models.user import User
from app.schemas.region import RegionCreate, RegionResponse


router = APIRouter(
    prefix="/regions",
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
    db: Session = Depends(get_db),
):
    new_region = Region(
        organization_id=organization_id,
        name=region.name,
        slug=region.slug,
    )

    db.add(new_region)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Region slug already exists for this organization",
        )

    db.refresh(new_region)

    return new_region

@router.get(
    "/{region_id}",
    response_model=RegionResponse,
)
async def get_region(
    region_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    region = db.scalar(
        select(Region).where(
            Region.id == region_id
        )
    )

    if region is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found",
        )

    return region

@router.get(
    "/organizations/{organization_id}",
    response_model=list[RegionResponse],
)
async def list_regions(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    regions = db.scalars(
        select(Region)
        .where(
            Region.organization_id == organization_id
        )
        .order_by(Region.id)
    ).all()

    return regions