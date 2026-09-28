"""grant organization update permission to organization admins

Revision ID: fbd55dbb4d00
Revises: 93307575da8d
Create Date: 2026-09-28 11:50:51.788458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbd55dbb4d00'
down_revision: Union[str, Sequence[str], None] = '93307575da8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT
                r.id,
                p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'Organization Admin'
              AND r.is_active = TRUE
              AND p.name = 'ORGANIZATION_UPDATE'
              AND p.is_active = TRUE
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions rp
                  WHERE rp.role_id = r.id
                    AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id
                FROM permissions
                WHERE name = 'ORGANIZATION_UPDATE'
            )
              AND role_id IN (
                  SELECT id
                  FROM roles
                  WHERE name = 'Organization Admin'
              )
            """
        )
    )
