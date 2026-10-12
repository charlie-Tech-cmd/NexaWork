"""Seed region permissions and grant them to active Organization Admin roles."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a41d9e6b7c20"
down_revision: Union[str, Sequence[str], None] = "c7e1a2b4d690"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create missing region permissions and grant active permissions."""
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (name, description, is_active, created_at)
            SELECT seeded.name, seeded.description, TRUE, NOW()
            FROM (
                SELECT 'REGION_VIEW' AS name, 'View regions' AS description
                UNION ALL
                SELECT 'REGION_CREATE', 'Create regions'
                UNION ALL
                SELECT 'REGION_UPDATE', 'Update regions'
            ) AS seeded
            WHERE NOT EXISTS (
                SELECT 1
                FROM permissions AS existing
                WHERE existing.name = seeded.name
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles AS r
            CROSS JOIN permissions AS p
            WHERE r.name = 'Organization Admin'
              AND r.is_active = TRUE
              AND p.name IN (
                  'REGION_VIEW',
                  'REGION_CREATE',
                  'REGION_UPDATE'
              )
              AND p.is_active = TRUE
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions AS rp
                  WHERE rp.role_id = r.id
                    AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    """Preserve permissions and grants whose prior ownership is unknown."""
    pass
