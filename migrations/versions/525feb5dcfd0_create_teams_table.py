"""create teams table

Revision ID: 525feb5dcfd0
Revises: 0b2aea69fb3f
Create Date: 2026-09-22 15:38:10.652237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '525feb5dcfd0'
down_revision: Union[str, Sequence[str], None] = '0b2aea69fb3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create teams table."""
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "department_id",
            "slug",
            name="uq_teams_department_slug",
        ),
    )

    op.create_index(
        op.f("ix_teams_department_id"),
        "teams",
        ["department_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop teams table."""
    op.drop_index(
        op.f("ix_teams_department_id"),
        table_name="teams",
    )
    op.drop_table("teams")
