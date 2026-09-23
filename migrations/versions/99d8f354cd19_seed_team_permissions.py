"""seed team permissions

Revision ID: 99d8f354cd19
Revises: 525feb5dcfd0
Create Date: 2026-09-23 11:25:50.115275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99d8f354cd19'
down_revision: Union[str, Sequence[str], None] = '525feb5dcfd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed team permissions."""
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (
                name,
                description,
                is_active,
                created_at
            )
            SELECT
                name,
                description,
                is_active,
                NOW()
            FROM (
                VALUES
                    (
                        'TEAM_VIEW',
                        'View teams',
                        TRUE
                    ),
                    (
                        'TEAM_CREATE',
                        'Create teams',
                        TRUE
                    ),
                    (
                        'TEAM_UPDATE',
                        'Update teams',
                        TRUE
                    )
            ) AS new_permissions(name, description, is_active)
            WHERE NOT EXISTS (
                SELECT 1
                FROM permissions
                WHERE permissions.name = new_permissions.name
            )
            """
        )
    )


def downgrade() -> None:
    """Remove team permissions."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN (
                'TEAM_VIEW',
                'TEAM_CREATE',
                'TEAM_UPDATE'
            )
            """
        )
    )