from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.department import Department
from app.models.region import Region
from app.models.team import Team


def create_team(
    db: Session,
    organization_id: int,
    department_id: int,
    name: str,
    slug: str,
) -> Team:
    department = db.scalar(
        select(Department)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Department.id == department_id,
            Department.is_active.is_(True),
            Branch.is_active.is_(True),
            Region.is_active.is_(True),
            Region.organization_id == organization_id,
        )
    )

    if department is None:
        raise ValueError("Department not found")

    new_team = Team(
        department_id=department_id,
        name=name,
        slug=slug,
    )
    db.add(new_team)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_team)
    return new_team


def list_teams(
    db: Session,
    organization_id: int,
    department_id: int,
) -> list[Team]:
    department = db.scalar(
        select(Department)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Department.id == department_id,
            Department.is_active.is_(True),
            Branch.is_active.is_(True),
            Region.is_active.is_(True),
            Region.organization_id == organization_id,
        )
    )

    if department is None:
        raise ValueError("Department not found")

    return db.scalars(
        select(Team)
        .where(
            Team.department_id == department_id,
            Team.is_active.is_(True),
        )
        .order_by(Team.id)
    ).all()


def update_team(
    db: Session,
    organization_id: int,
    team_id: int,
    name: str | None,
    slug: str | None,
    is_active: bool | None,
) -> Team:
    team = db.scalar(
        select(Team)
        .join(Department, Team.department_id == Department.id)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Team.id == team_id,
            Department.is_active.is_(True),
            Branch.is_active.is_(True),
            Region.is_active.is_(True),
            Region.organization_id == organization_id,
        )
    )

    if team is None:
        raise ValueError("Team not found")

    if name is not None:
        team.name = name

    if slug is not None:
        team.slug = slug

    if is_active is not None:
        team.is_active = is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(team)
    return team


def get_team(
    db: Session,
    organization_id: int,
    team_id: int,
) -> Team:
    team = db.scalar(
        select(Team)
        .join(Department, Team.department_id == Department.id)
        .join(Branch, Department.branch_id == Branch.id)
        .join(Region, Branch.region_id == Region.id)
        .where(
            Team.id == team_id,
            Team.is_active.is_(True),
            Department.is_active.is_(True),
            Branch.is_active.is_(True),
            Region.is_active.is_(True),
            Region.organization_id == organization_id,
        )
    )

    if team is None:
        raise ValueError("Team not found")

    return team
