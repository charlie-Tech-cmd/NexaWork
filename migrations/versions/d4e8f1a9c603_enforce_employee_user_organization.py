"""Enforce employee and user organization consistency."""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "d4e8f1a9c603"
down_revision: Union[str, Sequence[str], None] = "c29a4f1d7e62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Prevent employees from referencing users in another organization."""

    if not context.is_offline_mode():
        connection = op.get_bind()
        count = connection.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM employees e
                JOIN users u ON u.id = e.user_id
                WHERE u.is_super_admin = TRUE
                   OR e.organization_id IS DISTINCT FROM u.organization_id
                """
            )
        ).scalar_one()

        if count:
            raise RuntimeError(
                "Cannot enforce employee/user organization consistency: "
                f"{count} inconsistent employee row(s) found."
            )

    op.create_foreign_key(
        "fk_employees_user_organization",
        "employees",
        "users",
        ["user_id", "organization_id"],
        ["id", "organization_id"],
    )


def downgrade() -> None:
    """Remove the employee/user organization foreign key."""

    op.drop_constraint(
        "fk_employees_user_organization",
        "employees",
        type_="foreignkey",
    )
