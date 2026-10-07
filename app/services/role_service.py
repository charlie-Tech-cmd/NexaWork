from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions


def create_role(
    db: Session,
    organization_id: int,
    name: str,
    description: str | None,
) -> Role:
    new_role = Role(
        organization_id=organization_id,
        name=name,
        description=description,
    )

    db.add(new_role)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(new_role)
    return new_role


def list_roles(
    db: Session,
    organization_id: int,
) -> list[Role]:
    return db.scalars(
        select(Role)
        .where(Role.organization_id == organization_id)
        .order_by(Role.id)
    ).all()


def get_role(
    db: Session,
    organization_id: int,
    role_id: int,
) -> Role:
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )

    if role is None:
        raise ValueError("Role not found")

    return role


def update_role(
    db: Session,
    organization_id: int,
    role_id: int,
    name: str | None,
    description: str | None,
    is_active: bool | None,
) -> Role:
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )

    if role is None:
        raise ValueError("Role not found")

    if name is not None:
        role.name = name

    if description is not None:
        role.description = description

    if is_active is not None:
        role.is_active = is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(role)
    return role


def assign_permission_to_role(
    db: Session,
    organization_id: int,
    role_id: int,
    permission_id: int,
) -> None:
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )

    if role is None:
        raise ValueError("Role not found")

    permission = db.get(Permission, permission_id)

    if permission is None:
        raise ValueError("Permission not found")

    existing_assignment = db.execute(
        select(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    ).first()

    if existing_assignment is not None:
        raise ValueError("Permission already assigned to role")

    db.execute(
        role_permissions.insert().values(
            role_id=role_id,
            permission_id=permission_id,
        )
    )

    db.commit()


def list_role_permissions(
    db: Session,
    organization_id: int,
    role_id: int,
) -> list[Permission]:
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )

    if role is None:
        raise ValueError("Role not found")

    return db.scalars(
        select(Permission)
        .join(
            role_permissions,
            role_permissions.c.permission_id == Permission.id,
        )
        .where(role_permissions.c.role_id == role_id)
        .order_by(Permission.id)
    ).all()


def delete_role(
    db: Session,
    organization_id: int,
    role_id: int,
) -> None:
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )

    if role is None:
        raise ValueError("Role not found")

    db.delete(role)
    db.commit()


def remove_permission_from_role(
    db: Session,
    organization_id: int,
    role_id: int,
    permission_id: int,
) -> None:
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )

    if role is None:
        raise ValueError("Role not found")

    permission = db.get(Permission, permission_id)

    if permission is None:
        raise ValueError("Permission not found")

    existing_assignment = db.execute(
        select(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    ).first()

    if existing_assignment is None:
        raise ValueError("Permission is not assigned to role")

    db.execute(
        role_permissions.delete().where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    )

    db.commit()
