"""Provision organization admin and role-management permissions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2f697c73248a"
down_revision: Union[str, Sequence[str], None] = "a41d9e6b7c20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed missing permissions and grant them to eligible admin roles."""
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (name, description, is_active, created_at)
            SELECT seeded.name, seeded.description, TRUE, NOW()
            FROM (
                SELECT 'ROLE_VIEW' AS name, 'View roles' AS description
                UNION ALL
                SELECT 'ROLE_CREATE', 'Create roles'
                UNION ALL
                SELECT 'ROLE_UPDATE', 'Update roles'
                UNION ALL
                SELECT 'ROLE_DELETE', 'Delete roles'
                UNION ALL
                SELECT 'ROLE_ASSIGN_PERMISSION', 'Assign permissions to roles'
                UNION ALL
                SELECT 'ROLE_REMOVE_PERMISSION', 'Remove permissions from roles'
                UNION ALL
                SELECT 'ADMIN_ACCESS', 'Access administrative functions'
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
            SELECT DISTINCT r.id, p.id
            FROM roles AS r
            JOIN user_roles AS ur
              ON ur.role_id = r.id
            JOIN users AS u
              ON u.id = ur.user_id
             AND u.organization_id = r.organization_id
             AND u.is_active = TRUE
            CROSS JOIN permissions AS p
            WHERE r.organization_id IS NOT NULL
              AND r.name = 'Organization Admin'
              AND r.is_active = TRUE
              AND p.name IN (
                  'ROLE_VIEW',
                  'ROLE_CREATE',
                  'ROLE_UPDATE',
                  'ROLE_DELETE',
                  'ROLE_ASSIGN_PERMISSION',
                  'ROLE_REMOVE_PERMISSION',
                  'ADMIN_ACCESS'
              )
              AND p.is_active = TRUE
              AND (
                  SELECT COUNT(DISTINCT baseline.name)
                  FROM role_permissions AS baseline_rp
                  JOIN permissions AS baseline
                    ON baseline.id = baseline_rp.permission_id
                  WHERE baseline_rp.role_id = r.id
                    AND baseline.is_active = TRUE
                    AND baseline.name IN (
                        'USER_VIEW',
                        'USER_CREATE',
                        'USER_UPDATE',
                        'USER_DELETE'
                    )
              ) = 4
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions AS existing_rp
                  WHERE existing_rp.role_id = r.id
                    AND existing_rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    """Preserve seeded permissions and grants that may already be in use."""
    pass
