from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.region import Region


def create_region(
    db: Session,
    organization_id: int,
    name: str,
    slug: str,
) -> Region:
    new_region = Region(
        organization_id=organization_id,
        name=name,
        slug=slug,
    )

    db.add(new_region)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_region)
    return new_region


def get_region(
    db: Session,
    organization_id: int,
    region_id: int,
) -> Region:
    region = db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
        )
    )

    if region is None:
        raise ValueError("Region not found")

    return region


def list_regions(
    db: Session,
    organization_id: int,
) -> list[Region]:
    return db.scalars(
        select(Region)
        .where(
            Region.organization_id == organization_id,
            Region.is_active.is_(True),
        )
        .order_by(Region.id)
    ).all()


def update_region(
    db: Session,
    organization_id: int,
    region_id: int,
    name: str | None,
    slug: str | None,
    is_active: bool | None,
) -> Region:
    region = db.scalar(
        select(Region).where(
            Region.id == region_id,
            Region.organization_id == organization_id,
        )
    )

    if region is None:
        raise ValueError("Region not found")

    if name is not None:
        region.name = name

    if slug is not None:
        region.slug = slug

    if is_active is not None:
        region.is_active = is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(region)
    return region
