"""Add employee onboarding lifecycle tables and columns.

Revision ID: d9e1a4b7c230
Revises: 9c4a71e2b6d3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e1a4b7c230"
down_revision: Union[str, Sequence[str], None] = "9c4a71e2b6d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "email_verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="verified",
        ),
    )
    op.add_column(
        "employees",
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
            server_default="approved",
        ),
    )
    op.add_column(
        "employees",
        sa.Column(
            "account_status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "employees",
        sa.Column("verification_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("approval_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("account_status_reason", sa.String(length=255), nullable=True),
    )
    op.execute(
        """
        UPDATE employees
        SET account_status = 'disabled'
        WHERE is_active = FALSE
        """
    )
    op.create_check_constraint(
        "ck_employees_email_verification_status",
        "employees",
        "email_verification_status IN ('unverified', 'verified')",
    )
    op.create_check_constraint(
        "ck_employees_approval_status",
        "employees",
        "approval_status IN ('pending', 'approved', 'rejected')",
    )
    op.create_check_constraint(
        "ck_employees_account_status",
        "employees",
        "account_status IN ('active', 'disabled')",
    )
    op.create_index(
        "ix_employees_verification_token",
        "employees",
        ["verification_token"],
        unique=True,
    )

    op.create_table(
        "organization_registration_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_registration_codes_creator_organization",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_registration_codes_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            name="uq_organization_registration_code",
        ),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_registration_codes_id_organization",
        ),
    )
    op.create_index(
        "ix_organization_registration_codes_code",
        "organization_registration_codes",
        ["code"],
        unique=False,
    )
    op.create_index(
        "ix_organization_registration_codes_created_by_user_id",
        "organization_registration_codes",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_registration_codes_organization_id",
        "organization_registration_codes",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "employee_registration_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("registration_code_id", sa.Integer(), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("verification_token", sa.String(length=255), nullable=True),
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "email_verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "account_status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("approval_reason", sa.String(length=255), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("rejected_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "email_verification_status IN ('unverified', 'verified')",
            name="ck_registration_email_verification_status",
        ),
        sa.CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected')",
            name="ck_registration_approval_status",
        ),
        sa.CheckConstraint(
            "account_status IN ('active', 'disabled')",
            name="ck_registration_account_status",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_registration_requests_approver_organization",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_registration_requests_branch_organization",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_registration_requests_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id", "branch_id"],
            ["departments.id", "departments.branch_id"],
            name="fk_registration_requests_department_branch",
        ),
        sa.ForeignKeyConstraint(
            ["rejected_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_registration_requests_rejector_organization",
        ),
        sa.ForeignKeyConstraint(
            ["registration_code_id", "organization_id"],
            [
                "organization_registration_codes.id",
                "organization_registration_codes.organization_id",
            ],
            name="fk_registration_requests_code_organization",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "email",
            name="uq_employee_registration_email_org",
        ),
    )
    op.create_index(
        "ix_employee_registration_requests_branch_id",
        "employee_registration_requests",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_registration_requests_department_id",
        "employee_registration_requests",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_registration_requests_email",
        "employee_registration_requests",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_employee_registration_requests_organization_id",
        "employee_registration_requests",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_registration_requests_registration_code_id",
        "employee_registration_requests",
        ["registration_code_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_registration_requests_verification_token",
        "employee_registration_requests",
        ["verification_token"],
        unique=True,
    )

    op.create_table(
        "employee_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=False),
        sa.Column("invitation_token", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked', 'expired')",
            name="ck_employee_invitation_status",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_employee_invitations_branch_organization",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_employee_invitations_creator_organization",
        ),
        sa.ForeignKeyConstraint(
            ["department_id", "branch_id"],
            ["departments.id", "departments.branch_id"],
            name="fk_employee_invitations_department_branch",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_employee_invitations_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_employee_invitation_pending_email_org",
        "employee_invitations",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_employee_invitations_created_by_user_id",
        "employee_invitations",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_invitations_branch_id",
        "employee_invitations",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_invitations_department_id",
        "employee_invitations",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_invitations_email",
        "employee_invitations",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_employee_invitations_invitation_token",
        "employee_invitations",
        ["invitation_token"],
        unique=True,
    )
    op.create_index(
        "ix_employee_invitations_organization_id",
        "employee_invitations",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_employee_invitation_pending_email_org",
        table_name="employee_invitations",
    )
    op.drop_index(
        "ix_employee_invitations_department_id",
        table_name="employee_invitations",
    )
    op.drop_index(
        "ix_employee_invitations_branch_id",
        table_name="employee_invitations",
    )
    op.drop_index(
        "ix_employee_invitations_organization_id",
        table_name="employee_invitations",
    )
    op.drop_index(
        "ix_employee_invitations_invitation_token",
        table_name="employee_invitations",
    )
    op.drop_index(
        "ix_employee_invitations_email",
        table_name="employee_invitations",
    )
    op.drop_index(
        "ix_employee_invitations_created_by_user_id",
        table_name="employee_invitations",
    )
    op.drop_table("employee_invitations")

    op.drop_index(
        "ix_employee_registration_requests_verification_token",
        table_name="employee_registration_requests",
    )
    op.drop_index(
        "ix_employee_registration_requests_registration_code_id",
        table_name="employee_registration_requests",
    )
    op.drop_index(
        "ix_employee_registration_requests_organization_id",
        table_name="employee_registration_requests",
    )
    op.drop_index(
        "ix_employee_registration_requests_email",
        table_name="employee_registration_requests",
    )
    op.drop_index(
        "ix_employee_registration_requests_department_id",
        table_name="employee_registration_requests",
    )
    op.drop_index(
        "ix_employee_registration_requests_branch_id",
        table_name="employee_registration_requests",
    )
    op.drop_table("employee_registration_requests")

    op.drop_index(
        "ix_organization_registration_codes_organization_id",
        table_name="organization_registration_codes",
    )
    op.drop_index(
        "ix_organization_registration_codes_created_by_user_id",
        table_name="organization_registration_codes",
    )
    op.drop_index(
        "ix_organization_registration_codes_code",
        table_name="organization_registration_codes",
    )
    op.drop_table("organization_registration_codes")

    op.drop_index("ix_employees_verification_token", table_name="employees")
    op.drop_constraint(
        "ck_employees_account_status",
        "employees",
        type_="check",
    )
    op.drop_constraint(
        "ck_employees_approval_status",
        "employees",
        type_="check",
    )
    op.drop_constraint(
        "ck_employees_email_verification_status",
        "employees",
        type_="check",
    )
    op.drop_column("employees", "approval_reason")
    op.drop_column("employees", "account_status_reason")
    op.drop_column("employees", "verification_token")
    op.drop_column("employees", "account_status")
    op.drop_column("employees", "approval_status")
    op.drop_column("employees", "email_verification_status")
