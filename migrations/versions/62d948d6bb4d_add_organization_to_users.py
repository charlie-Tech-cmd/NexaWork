"""add organization to users

Revision ID: 62d948d6bb4d
Revises: 1fd3cfef7c94
Create Date: 2026-09-19 10:48:12.424513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "62d948d6bb4d"
down_revision: Union[str, Sequence[str], None] = "1fd3cfef7c94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_users_organization_id",
        "users",
        ["organization_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_users_organization_id_organizations",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET organization_id = 1
            WHERE organization_id IS NULL
            """
        )
    )

    op.alter_column(
        "users",
        "organization_id",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_users_organization_id_organizations",
        "users",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_users_organization_id",
        table_name="users",
    )

    op.drop_column(
        "users",
        "organization_id",
    )