"""seed employee update permission

Revision ID: 38d0ff04ba8c
Revises: 97d023bf0453
Create Date: 2026-09-23 18:50:18.943256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38d0ff04ba8c'
down_revision: Union[str, Sequence[str], None] = '97d023bf0453'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed employee update permission."""
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
                        'EMPLOYEE_UPDATE',
                        'Update employees',
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
    """Remove employee update permission."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name = 'EMPLOYEE_UPDATE'
            """
        )
    )
