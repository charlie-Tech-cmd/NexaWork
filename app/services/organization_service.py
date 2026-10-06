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
