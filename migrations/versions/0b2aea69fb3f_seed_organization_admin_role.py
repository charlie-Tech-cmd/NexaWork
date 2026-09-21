"""seed organization admin role

Revision ID: 0b2aea69fb3f
Revises: a4aeb569a01b
Create Date: 2026-09-21 23:12:06.586952
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b2aea69fb3f"
down_revision: Union[str, Sequence[str], None] = "a4aeb569a01b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create and assign the initial Organization Admin role."""

    op.execute(
        sa.text(
            """
            INSERT INTO roles (
                organization_id,
                name,
                description,
                is_active,
                created_at
            )
            SELECT
                1,
                'Organization Admin',
                'Manage users and organization-level administration',
                TRUE,
                NOW()
            WHERE NOT EXISTS (
                SELECT 1
                FROM roles
                WHERE organization_id = 1
                  AND name = 'Organization Admin'
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
            WHERE r.organization_id = 1
              AND r.name = 'Organization Admin'
              AND p.name IN (
                  'USER_VIEW',
                  'USER_CREATE',
                  'USER_UPDATE',
                  'USER_DELETE'
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

    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT
                1,
                r.id
            FROM roles r
            WHERE r.organization_id = 1
              AND r.name = 'Organization Admin'
              AND NOT EXISTS (
                  SELECT 1
                  FROM user_roles ur
                  WHERE ur.user_id = 1
                    AND ur.role_id = r.id
              )
            """
        )
    )


def downgrade() -> None:
    """Remove the initial Organization Admin role and its assignments."""

    op.execute(
        sa.text(
            """
            DELETE FROM user_roles
            WHERE user_id = 1
              AND role_id IN (
                  SELECT id
                  FROM roles
                  WHERE organization_id = 1
                    AND name = 'Organization Admin'
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (
                SELECT id
                FROM roles
                WHERE organization_id = 1
                  AND name = 'Organization Admin'
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE organization_id = 1
              AND name = 'Organization Admin'
            """
        )
    )
