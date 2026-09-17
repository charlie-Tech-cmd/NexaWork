from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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