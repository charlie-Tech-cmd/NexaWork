from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization


def create_organization(
    db: Session,
    name: str,
    slug: str,
) -> Organization:
    new_organization = Organization(
        name=name,
        slug=slug,
    )

    db.add(new_organization)
    db.commit()
    db.refresh(new_organization)

    return new_organization


def update_organization_status(
    db: Session,
    organization_id: int,
    is_active: bool,
) -> Organization:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
        )
    )

    if organization is None:
        raise ValueError("Organization not found")

    organization.is_active = is_active
    db.commit()
    db.refresh(organization)

    return organization


def get_organization(
    db: Session,
    organization_id: int,
    current_organization_id: int,
) -> Organization:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.id == current_organization_id,
        )
    )

    if organization is None:
        raise ValueError("Organization not found")

    return organization
