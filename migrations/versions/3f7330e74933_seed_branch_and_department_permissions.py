"""seed branch and department permissions

Revision ID: 3f7330e74933
Revises: 9eea792a84e7
Create Date: 2026-10-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3f7330e74933"
down_revision: Union[str, Sequence[str], None] = "9eea792a84e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed branch and department permissions."""
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
                        'BRANCH_VIEW',
                        'View branches',
                        TRUE
                    ),
                    (
                        'BRANCH_CREATE',
                        'Create branches',
                        TRUE
                    ),
                    (
                        'BRANCH_UPDATE',
                        'Update branches',
                        TRUE
                    ),
                    (
                        'BRANCH_DELETE',
                        'Delete branches',
                        TRUE
                    ),
                    (
                        'DEPARTMENT_VIEW',
                        'View departments',
                        TRUE
                    ),
                    (
                        'DEPARTMENT_CREATE',
                        'Create departments',
                        TRUE
                    ),
                    (
                        'DEPARTMENT_UPDATE',
                        'Update departments',
                        TRUE
                    ),
                    (
                        'DEPARTMENT_DELETE',
                        'Delete departments',
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
              AND p.name IN (
                  'BRANCH_VIEW',
                  'BRANCH_CREATE',
                  'BRANCH_UPDATE',
                  'BRANCH_DELETE',
                  'DEPARTMENT_VIEW',
                  'DEPARTMENT_CREATE',
                  'DEPARTMENT_UPDATE',
                  'DEPARTMENT_DELETE'
              )
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
    """Remove branch and department permissions from Organization Admin roles."""
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id
                FROM permissions
                WHERE name IN (
                    'BRANCH_VIEW',
                    'BRANCH_CREATE',
                    'BRANCH_UPDATE',
                    'BRANCH_DELETE',
                    'DEPARTMENT_VIEW',
                    'DEPARTMENT_CREATE',
                    'DEPARTMENT_UPDATE',
                    'DEPARTMENT_DELETE'
                )
            )
              AND role_id IN (
                  SELECT id
                  FROM roles
                  WHERE name = 'Organization Admin'
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN (
                'BRANCH_VIEW',
                'BRANCH_CREATE',
                'BRANCH_UPDATE',
                'BRANCH_DELETE',
                'DEPARTMENT_VIEW',
                'DEPARTMENT_CREATE',
                'DEPARTMENT_UPDATE',
                'DEPARTMENT_DELETE'
            )
            """
        )
    )
