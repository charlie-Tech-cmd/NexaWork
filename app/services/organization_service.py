from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


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


def update_organization(
    db: Session,
    organization: Organization,
    name: str | None,
    slug: str | None,
) -> Organization:
    if name is not None:
        organization.name = name

    if slug is not None:
        organization.slug = slug

    db.commit()
    db.refresh(organization)

    return organization


def onboard_organization(
    db: Session,
    organization_name: str,
    organization_slug: str,
    admin_email: str,
    admin_password: str,
    admin_full_name: str,
) -> dict:
    existing_organization = db.scalar(
        select(Organization).where(
            Organization.slug == organization_slug,
        )
    )

    if existing_organization is not None:
        raise ValueError("Organization slug already exists")

    existing_user = db.scalar(
        select(User).where(
            User.email == admin_email,
        )
    )

    if existing_user is not None:
        raise ValueError("Email already registered")

    new_organization = Organization(
        name=organization_name,
        slug=organization_slug,
    )
    db.add(new_organization)
    db.flush()

    new_admin = User(
        organization_id=new_organization.id,
        email=admin_email,
        password_hash=hash_password(admin_password),
        full_name=admin_full_name,
        is_active=True,
    )
    db.add(new_admin)
    db.flush()

    admin_role = Role(
        organization_id=new_organization.id,
        name="Organization Admin",
        description="Manage users and organization-level administration",
        is_active=True,
    )
    db.add(admin_role)
    db.flush()

    permissions = db.scalars(
        select(Permission).where(
            Permission.name.in_(
                [
                    "USER_VIEW",
                    "USER_CREATE",
                    "USER_UPDATE",
                    "USER_DELETE",
                    "ORGANIZATION_UPDATE",
                ]
            ),
            Permission.is_active.is_(True),
        )
    ).all()

    if len(permissions) != 5:
        db.rollback()
        raise RuntimeError("Required permissions are not configured")

    for permission in permissions:
        db.execute(
            role_permissions.insert().values(
                role_id=admin_role.id,
                permission_id=permission.id,
            )
        )

    db.execute(
        user_roles.insert().values(
            user_id=new_admin.id,
            role_id=admin_role.id,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_organization)
    db.refresh(new_admin)

    return {
        "organization": new_organization,
        "admin": new_admin,
    }
