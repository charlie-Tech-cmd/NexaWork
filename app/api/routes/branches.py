from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.branch import Branch
from app.models.user import User
from app.schemas.branch import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
)


router = APIRouter(
    prefix="/branches",
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
    db: Session = Depends(get_db),
):
    new_branch = Branch(
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
    db: Session = Depends(get_db),
):
    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id
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
    db: Session = Depends(get_db),
):
    branches = db.scalars(
        select(Branch)
        .where(
            Branch.region_id == region_id
        )
        .order_by(Branch.id)
    ).all()

    return branches


@router.put(
    "/{branch_id}",
    response_model=BranchResponse,
)
async def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    if branch_data.name is not None:
        branch.name = branch_data.name

    if branch_data.slug is not None:
        branch.slug = branch_data.slug

    if branch_data.is_active is not None:
        branch.is_active = branch_data.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Branch slug already exists for this region",
        )

    db.refresh(branch)

    return branch
    