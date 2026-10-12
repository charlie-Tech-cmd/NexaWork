"""Grant team permissions to all active Organization Admin roles."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e1a2b4d690"
down_revision: Union[str, Sequence[str], None] = "3f7330e74933"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Grant missing team permissions across all organizations."""
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
                  'TEAM_VIEW',
                  'TEAM_CREATE',
                  'TEAM_UPDATE'
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
    """Preserve grants whose prior existence cannot be established."""
    pass
