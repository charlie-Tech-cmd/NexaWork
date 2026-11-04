"""Add index for organization registration approval lists

Revision ID: d649ac3f1082
Revises: b52d10e7a4c9
Create Date: 2026-11-04 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d649ac3f1082"
down_revision: Union[str, Sequence[str], None] = "b52d10e7a4c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_users_org_lifecycle_approval_created",
        "users",
        [
            "organization_id",
            "lifecycle_managed",
            "approval_status",
            "created_at",
            "id",
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_org_lifecycle_approval_created",
        table_name="users",
    )
