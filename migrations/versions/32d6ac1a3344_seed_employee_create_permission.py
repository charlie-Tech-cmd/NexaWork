"""seed employee create permission

Revision ID: 32d6ac1a3344
Revises: fd5dc1641f56
Create Date: 2026-09-23 17:26:12.483131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32d6ac1a3344'
down_revision: Union[str, Sequence[str], None] = 'fd5dc1641f56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed employee create permission."""
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
                        'EMPLOYEE_CREATE',
                        'Create employees',
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
    """Remove employee create permission."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name = 'EMPLOYEE_CREATE'
            """
        )
    )
