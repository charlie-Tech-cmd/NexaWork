"""seed admin access permission

Revision ID: 376b788b8009
Revises: 8c65456d9446
Create Date: 2026-09-26 02:05:28.214915

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "new_revision_id"
down_revision = "8c65456d9446"


def upgrade():
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
                'ADMIN_ACCESS',
                'Access administrative portal',
                TRUE,
                NOW()
            WHERE NOT EXISTS (
                SELECT 1
                FROM permissions
                WHERE name = 'ADMIN_ACCESS'
            )
            """
        )
    )


def downgrade():
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name = 'ADMIN_ACCESS'
            """
        )
    )