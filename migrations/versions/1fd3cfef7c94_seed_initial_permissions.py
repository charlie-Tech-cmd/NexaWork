"""seed initial permissions

Revision ID: 1fd3cfef7c94
Revises: bd9125b5ea95
Create Date: 2026-09-19 07:34:00.124069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fd3cfef7c94'
down_revision: Union[str, Sequence[str], None] = 'bd9125b5ea95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial permissions."""
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
                        'USER_VIEW',
                        'View users',
                        TRUE
                    ),
                    (
                        'USER_CREATE',
                        'Create users',
                        TRUE
                    ),
                    (
                        'USER_UPDATE',
                        'Update users',
                        TRUE
                    ),
                    (
                        'USER_DELETE',
                        'Delete users',
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
    """Remove initial permissions."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN (
                'USER_VIEW',
                'USER_CREATE',
                'USER_UPDATE',
                'USER_DELETE'
            )
            """
        )
    )