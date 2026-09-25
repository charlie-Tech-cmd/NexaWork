"""seed permission management permissions

Revision ID: 646ed07bb03a
Revises: 99d8f354cd19
Create Date: 2026-09-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "646ed07bb03a"
down_revision: Union[str, Sequence[str], None] = "38d0ff04ba8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed permission management permissions."""
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
                        'PERMISSION_VIEW',
                        'View permissions',
                        TRUE
                    ),
                    (
                        'PERMISSION_CREATE',
                        'Create permissions',
                        TRUE
                    ),
                    (
                        'PERMISSION_UPDATE',
                        'Update permissions',
                        TRUE
                    ),
                    (
                        'PERMISSION_DELETE',
                        'Delete permissions',
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
    """Remove permission management permissions."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN (
                'PERMISSION_VIEW',
                'PERMISSION_CREATE',
                'PERMISSION_UPDATE',
                'PERMISSION_DELETE'
            )
            """
        )
    )