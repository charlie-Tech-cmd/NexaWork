"""seed role management permissions

Revision ID: 8c65456d9446
Revises: d96da2e50616
Create Date: 2026-09-25 22:48:44.026720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c65456d9446'
down_revision: Union[str, Sequence[str], None] = 'd96da2e50616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed role management permissions."""
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
                        'ROLE_VIEW',
                        'View roles',
                        TRUE
                    ),
                    (
                        'ROLE_CREATE',
                        'Create roles',
                        TRUE
                    ),
                    (
                        'ROLE_UPDATE',
                        'Update roles',
                        TRUE
                    ),
                    (
                        'ROLE_DELETE',
                        'Delete roles',
                        TRUE
                    ),
                    (
                        'ROLE_ASSIGN_PERMISSION',
                        'Assign permissions to roles',
                        TRUE
                    ),
                    (
                        'ROLE_REMOVE_PERMISSION',
                        'Remove permissions from roles',
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
    """Remove role management permissions."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN (
                'ROLE_VIEW',
                'ROLE_CREATE',
                'ROLE_UPDATE',
                'ROLE_DELETE',
                'ROLE_ASSIGN_PERMISSION',
                'ROLE_REMOVE_PERMISSION'
            )
            """
        )
    )