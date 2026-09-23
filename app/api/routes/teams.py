from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    get_current_user,
    require_permission,
)

from app.db.session import get_db
from app.models.department import Department
from app.models.branch import Branch
from app.models.organization import Organization
from app.models.region import Region
from app.models.team import Team
from app.models.user import User
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate

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
    department = db.scalar(
        select(Department)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Department.id == department_id,
            Region.organization_id == current_organization.id,
        )
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    if team.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department ID does not match the URL",
        )

    new_team = Team(
        department_id=department_id,
        name=team.name,
        slug=team.slug,
    )

    db.add(new_team)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team slug already exists for this department",
        )

    db.refresh(new_team)

    return new_team

@router.get(
    "/departments/{department_id}",
    response_model=list[TeamResponse],
)
async def list_teams(
    department_id: int,
    current_user: User = Depends(
        require_permission("TEAM_VIEW"),
    ),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    department = db.scalar(
        select(Department)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Department.id == department_id,
            Region.organization_id == current_organization.id,
        )
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    teams = db.scalars(
        select(Team)
        .where(Team.department_id == department_id)
        .order_by(Team.id)
    ).all()

    return teams

@router.put(
    "/{team_id}",
    response_model=TeamResponse,
)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(
        require_permission("TEAM_UPDATE"),
    ),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    team = db.scalar(
        select(Team)
        .join(Department, Team.department_id == Department.id)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Team.id == team_id,
            Region.organization_id == current_organization.id,
        )
    )

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if team_data.name is not None:
        team.name = team_data.name

    if team_data.slug is not None:
        team.slug = team_data.slug

    if team_data.is_active is not None:
        team.is_active = team_data.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team slug already exists for this department",
        )

    db.refresh(team)

    return team

@router.get(
    "/{team_id}",
    response_model=TeamResponse,
)
async def get_team(
    team_id: int,
    current_user: User = Depends(
        require_permission("TEAM_VIEW"),
    ),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    team = db.scalar(
        select(Team)
        .join(Department, Team.department_id == Department.id)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Team.id == team_id,
            Region.organization_id == current_organization.id,
        )
    )

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return team
