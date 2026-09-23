"""seed employee view permission

Revision ID: 97d023bf0453
Revises: 32d6ac1a3344
Create Date: 2026-09-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "97d023bf0453"
down_revision: Union[str, Sequence[str], None] = "32d6ac1a3344"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed employee view permission."""
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
                        'EMPLOYEE_VIEW',
                        'View employees',
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
    """Remove employee view permission."""
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name = 'EMPLOYEE_VIEW'
            """
        )
    )
