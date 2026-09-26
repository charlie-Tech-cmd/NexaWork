"""add organization ownership to branch department employee

Revision ID: 733fefc0a662
Revises: new_revision_id
Create Date: 2026-09-26 03:40:34.597411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '733fefc0a662'
down_revision: Union[str, Sequence[str], None] = 'new_revision_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable columns first
    op.add_column(
        "branches",
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "employees",
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Backfill existing data
    op.execute("""
        UPDATE branches
        SET organization_id = regions.organization_id
        FROM regions
        WHERE branches.region_id = regions.id
    """)

    op.execute("""
        UPDATE employees
        SET organization_id = branches.organization_id
        FROM branches
        WHERE employees.branch_id = branches.id
    """)

    # Make columns required
    op.alter_column(
        "branches",
        "organization_id",
        nullable=False,
    )

    op.alter_column(
        "employees",
        "organization_id",
        nullable=False,
    )

    # Add constraints
    op.create_index(
        op.f("ix_branches_organization_id"),
        "branches",
        ["organization_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_employees_organization_id"),
        "employees",
        ["organization_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_branches_organization_id",
        "branches",
        "organizations",
        ["organization_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_employees_organization_id",
        "employees",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    
def downgrade() -> None:
    op.drop_constraint(
        'fk_employees_organization_id',
        'employees',
        type_='foreignkey',
    )
    op.drop_index(
        op.f('ix_employees_organization_id'),
        table_name='employees',
    )
    op.drop_column(
        'employees',
        'organization_id',
    )

    op.drop_constraint(
        'fk_branches_organization_id',
        'branches',
        type_='foreignkey',
    )
    op.drop_index(
        op.f('ix_branches_organization_id'),
        table_name='branches',
    )
    op.drop_column(
        'branches',
        'organization_id',
    )