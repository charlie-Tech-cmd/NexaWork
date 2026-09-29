"""add super admin user boundary

Revision ID: 164302bddb26
Revises: fbd55dbb4d00
Create Date: 2026-09-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "164302bddb26"
down_revision: Union[str, Sequence[str], None] = "fbd55dbb4d00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the platform-level Super Admin boundary."""

    op.add_column(
        "users",
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.alter_column(
        "users",
        "organization_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.create_check_constraint(
        "ck_users_super_admin_organization",
        "users",
        sa.or_(
            sa.and_(
                sa.column("is_super_admin") == sa.false(),
                sa.column("organization_id").is_not(None),
            ),
            sa.and_(
                sa.column("is_super_admin") == sa.true(),
                sa.column("organization_id").is_(None),
            ),
        ),
    )

    op.alter_column(
        "users",
        "is_super_admin",
        server_default=None,
    )


def downgrade() -> None:
    """Remove the platform-level Super Admin boundary."""

    super_admin_count = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM users
            WHERE is_super_admin = TRUE
            """
        )
    ).scalar_one()

    if super_admin_count:
        raise RuntimeError(
            "Cannot downgrade while Super Admin users exist."
        )

    op.drop_constraint(
        "ck_users_super_admin_organization",
        "users",
        type_="check",
    )

    op.alter_column(
        "users",
        "organization_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column(
        "users",
        "is_super_admin",
    )
