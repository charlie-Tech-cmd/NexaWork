"""Add user lifecycle state

Revision ID: a91d4e6c2f80
Revises: 9c4a71e2b6d3
Create Date: 2026-11-04 10:46:35.600000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a91d4e6c2f80"
down_revision: Union[str, Sequence[str], None] = "9c4a71e2b6d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "lifecycle_managed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "approval_status",
            sa.String(length=16),
            nullable=False,
            server_default="approved",
        ),
    )
    op.alter_column("users", "lifecycle_managed", server_default=None)
    op.alter_column("users", "approval_status", server_default=None)
    op.create_check_constraint(
        "ck_users_approval_status",
        "users",
        """
        approval_status IN ('pending', 'approved', 'rejected')
        AND (
            lifecycle_managed = TRUE
            OR approval_status = 'approved'
        )
        """,
    )
    op.create_check_constraint(
        "ck_users_lifecycle_managed_tenant",
        "users",
        """
        lifecycle_managed = FALSE
        OR (
            is_super_admin = FALSE
            AND organization_id IS NOT NULL
        )
        """,
    )
    op.create_check_constraint(
        "ck_users_lifecycle_active_eligible",
        "users",
        """
        lifecycle_managed = FALSE
        OR is_active = FALSE
        OR (
            approval_status = 'approved'
            AND email_verified_at IS NOT NULL
        )
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_lifecycle_active_eligible",
        "users",
        type_="check",
    )
    op.drop_constraint(
        "ck_users_lifecycle_managed_tenant",
        "users",
        type_="check",
    )
    op.drop_constraint(
        "ck_users_approval_status",
        "users",
        type_="check",
    )
    op.drop_column("users", "approval_status")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "lifecycle_managed")
