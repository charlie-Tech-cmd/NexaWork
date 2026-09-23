"""grant team permissions to organization admin

Revision ID: fd5dc1641f56
Revises: 99d8f354cd19
Create Date: 2026-09-23 11:38:11.667170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd5dc1641f56'
down_revision: Union[str, Sequence[str], None] = '99d8f354cd19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Grant team permissions to Organization Admin."""
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT
                r.id,
                p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.organization_id = 1
              AND r.name = 'Organization Admin'
              AND p.name IN (
                  'TEAM_VIEW',
                  'TEAM_CREATE',
                  'TEAM_UPDATE'
              )
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
    """Remove team permissions from Organization Admin."""
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r, permissions p
            WHERE rp.role_id = r.id
              AND rp.permission_id = p.id
              AND r.organization_id = 1
              AND r.name = 'Organization Admin'
              AND p.name IN (
                  'TEAM_VIEW',
                  'TEAM_CREATE',
                  'TEAM_UPDATE'
              )
            """
        )
    )