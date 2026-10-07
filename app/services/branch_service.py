from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.region import Region


def create_branch(
    db: Session,
    organization_id: int,
    region_id: int,
    name: str,
    slug: str,
) -> Branch:
    region = db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
        )
    )

    if region is None:
        raise ValueError("Region not found")

    new_branch = Branch(
        organization_id=organization_id,
        region_id=region_id,
        name=name,
        slug=slug,
    )

    db.add(new_branch)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_branch)

    return new_branch


def get_branch(
    db: Session,
    organization_id: int,
    branch_id: int,
) -> Branch:
    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.organization_id == organization_id,
        )
    )

    if branch is None:
        raise ValueError("Branch not found")

    return branch


def list_region_branches(
    db: Session,
    organization_id: int,
    region_id: int,
) -> list[Branch]:
    region = db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
        )
    )

    if region is None:
        raise ValueError("Region not found")

    branches = db.scalars(
        select(Branch)
        .where(
            Branch.region_id == region_id,
            Branch.organization_id == organization_id,
        )
        .order_by(Branch.id)
    ).all()

    return branches
