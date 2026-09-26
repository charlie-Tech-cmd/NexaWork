from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization, get_current_user
from app.db.session import get_db
from app.models.branch import Branch
from app.models.organization import Organization
from app.models.region import Region
from app.models.user import User
from app.schemas.branch import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
)


router = APIRouter(
    prefix="/api/v1/branches",
    tags=["branches"],
)


@router.post(
    "/regions/{region_id}",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch(
    region_id: int,
    branch: BranchCreate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    region = db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.organization_id == current_organization.id,
        )
    )

    if region is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found",
        )

    new_branch = Branch(
        organization_id=current_organization.id,
        region_id=region_id,
        name=branch.name,
        slug=branch.slug,
    )

    db.add(new_branch)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Branch slug already exists for this region",
        )

    db.refresh(new_branch)

    return new_branch


@router.get(
    "/{branch_id}",
    response_model=BranchResponse,
)
async def get_branch(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.organization_id == current_organization.id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    return branch


@router.get(
    "/regions/{region_id}",
    response_model=list[BranchResponse],
)
async def list_branches(
    region_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    region = db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.organization_id == current_organization.id,
        )
    )

    if region is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found",
        )

    branches = db.scalars(
        select(Branch)
        .where(
            Branch.region_id == region_id,
            Branch.organization_id == current_organization.id,
        )
        .order_by(Branch.id)
    ).all()

    return branches