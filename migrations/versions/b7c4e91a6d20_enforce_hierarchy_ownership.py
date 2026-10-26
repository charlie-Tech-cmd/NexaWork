"""Enforce organization and branch consistency in hierarchy references."""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "b7c4e91a6d20"
down_revision: Union[str, Sequence[str], None] = "2f697c73248a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite keys and foreign keys enforcing hierarchy ownership."""

    # Refuse to install constraints if existing rows violate the hierarchy.
    checks = (
        (
            "branches.region_organization_mismatch",
            """
            SELECT COUNT(*)
            FROM branches b
            JOIN regions r ON r.id = b.region_id
            WHERE b.organization_id <> r.organization_id
            """,
        ),
        (
            "employees.branch_organization_mismatch",
            """
            SELECT COUNT(*)
            FROM employees e
            JOIN branches b ON b.id = e.branch_id
            WHERE e.organization_id <> b.organization_id
            """,
        ),
        (
            "employees.department_branch_mismatch",
            """
            SELECT COUNT(*)
            FROM employees e
            JOIN departments d ON d.id = e.department_id
            WHERE e.branch_id <> d.branch_id
            """,
        ),
    )

    # Offline SQL generation has no live database connection.
    # Keep the data-integrity preflight for actual online upgrades.
    if not context.is_offline_mode():
        connection = op.get_bind()
        for label, statement in checks:
            count = connection.execute(sa.text(statement)).scalar_one()
            if count:
                raise RuntimeError(
                    f"Cannot enforce hierarchy constraints: {label} "
                    f"has {count} inconsistent row(s)."
                )

    op.create_unique_constraint(
        "uq_regions_id_organization",
        "regions",
        ["id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_branches_id_organization",
        "branches",
        ["id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_departments_id_branch",
        "departments",
        ["id", "branch_id"],
    )

    op.create_foreign_key(
        "fk_branches_region_organization",
        "branches",
        "regions",
        ["region_id", "organization_id"],
        ["id", "organization_id"],
    )
    op.create_foreign_key(
        "fk_employees_branch_organization",
        "employees",
        "branches",
        ["branch_id", "organization_id"],
        ["id", "organization_id"],
    )
    op.create_foreign_key(
        "fk_employees_department_branch",
        "employees",
        "departments",
        ["department_id", "branch_id"],
        ["id", "branch_id"],
    )


def downgrade() -> None:
    """Remove only the constraints introduced by this migration."""

    op.drop_constraint(
        "fk_employees_department_branch",
        "employees",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_employees_branch_organization",
        "employees",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_branches_region_organization",
        "branches",
        type_="foreignkey",
    )

    op.drop_constraint(
        "uq_departments_id_branch",
        "departments",
        type_="unique",
    )
    op.drop_constraint(
        "uq_branches_id_organization",
        "branches",
        type_="unique",
    )
    op.drop_constraint(
        "uq_regions_id_organization",
        "regions",
        type_="unique",
    )
