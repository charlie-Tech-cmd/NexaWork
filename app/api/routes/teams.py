from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    get_current_user,
    require_permission,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.services.team_service import (
    create_team as create_team_service,
    get_team as get_team_service,
    list_teams as list_teams_service,
    update_team as update_team_service,
)

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
)


@router.post(
    "/departments/{department_id}",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team(
    department_id: int,
    team: TeamCreate,
    current_user: User = Depends(
        require_permission("TEAM_CREATE"),
    ),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    if team.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department ID does not match the URL",
        )

    try:
        return create_team_service(
            db,
            current_organization.id,
            department_id,
            team.name,
            team.slug,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team slug already exists for this department",
        )


@router.get(
    "/departments/{department_id}",
    response_model=list[TeamResponse],
)
async def list_teams(
    department_id: int,
    current_user: User = Depends(require_permission("TEAM_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return list_teams_service(
            db,
            current_organization.id,
            department_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.put(
    "/{team_id}",
    response_model=TeamResponse,
)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(require_permission("TEAM_UPDATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return update_team_service(
            db,
            current_organization.id,
            team_id,
            team_data.name,
            team_data.slug,
            team_data.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Team slug already exists for this department",
        )


@router.get(
    "/{team_id}",
    response_model=TeamResponse,
)
async def get_team(
    team_id: int,
    current_user: User = Depends(require_permission("TEAM_VIEW")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return get_team_service(
            db,
            current_organization.id,
            team_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )