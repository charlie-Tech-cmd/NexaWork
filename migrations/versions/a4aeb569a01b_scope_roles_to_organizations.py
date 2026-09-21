"""scope roles to organizations

Revision ID: a4aeb569a01b
Revises: 62d948d6bb4d
Create Date: 2026-09-21 12:00:17.816422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4aeb569a01b"
down_revision: Union[str, Sequence[str], None] = "62d948d6bb4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "roles",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        op.f("ix_roles_organization_id"),
        "roles",
        ["organization_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_roles_organization_id",
        "roles",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        """
        UPDATE roles
        SET organization_id = (
            SELECT u.organization_id
            FROM user_roles ur
            JOIN users u ON u.id = ur.user_id
            WHERE ur.role_id = roles.id
            LIMIT 1
        )
        WHERE organization_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE roles
        SET organization_id = (
            SELECT MIN(id)
            FROM organizations
        )
        WHERE organization_id IS NULL
        AND (SELECT COUNT(*) FROM organizations) = 1
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM roles
                WHERE organization_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot scope all roles to an organization';
            END IF;
        END
        $$;
        """
    )

    op.alter_column(
        "roles",
        "organization_id",
        nullable=False,
    )

    op.drop_index(
        op.f("ix_roles_name"),
        table_name="roles",
    )

    op.create_index(
        "ix_roles_name",
        "roles",
        ["name"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_roles_organization_name",
        "roles",
        ["organization_id", "name"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_roles_organization_name",
        "roles",
        type_="unique",
    )

    op.drop_index(
        op.f("ix_roles_name"),
        table_name="roles",
    )

    op.create_index(
        op.f("ix_roles_name"),
        "roles",
        ["name"],
        unique=True,
    )

    op.drop_constraint(
        "fk_roles_organization_id",
        "roles",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_roles_organization_id"),
        table_name="roles",
    )

    op.drop_column(
        "roles",
        "organization_id",
    )