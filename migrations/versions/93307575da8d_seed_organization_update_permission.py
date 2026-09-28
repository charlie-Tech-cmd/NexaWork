"""seed organization update permission

Revision ID: 93307575da8d
Revises: 733fefc0a662
Create Date: 2026-09-28 11:32:53.474517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93307575da8d'
down_revision: Union[str, Sequence[str], None] = '733fefc0a662'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
                'ORGANIZATION_UPDATE',
                'Update organization settings',
                TRUE,
                NOW()
            WHERE NOT EXISTS (
                SELECT 1
                FROM permissions
                WHERE name = 'ORGANIZATION_UPDATE'
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name = 'ORGANIZATION_UPDATE'
            """
        )
    )
