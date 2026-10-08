from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization, require_permission
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.branch import (
    BranchCreate,
    BranchResponse,
)
from app.services.branch_service import (
    create_branch as create_branch_service,
    get_branch as get_branch_service,
    list_region_branches as list_region_branches_service,
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
    current_user: User = Depends(require_permission("BRANCH_CREATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return create_branch_service(
            db,
            current_organization.id,
            region_id,
            branch.name,
            branch.slug,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Branch slug already exists for this region",
        )


@router.get(
    "/{branch_id}",
    response_model=BranchResponse,
)
async def get_branch(
    branch_id: int,
    current_user: User = Depends(require_permission("BRANCH_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return get_branch_service(
            db,
            current_organization.id,
            branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/regions/{region_id}",
    response_model=list[BranchResponse],
)
async def list_branches(
    region_id: int,
    current_user: User = Depends(require_permission("BRANCH_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return list_region_branches_service(
            db,
            current_organization.id,
            region_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
