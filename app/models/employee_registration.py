from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmployeeRegistrationRequest(Base):
    __tablename__ = "employee_registration_requests"

    __table_args__ = (
        CheckConstraint(
            "email_verification_status IN ('unverified', 'verified')",
            name="ck_registration_email_verification_status",
        ),
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected')",
            name="ck_registration_approval_status",
        ),
        CheckConstraint(
            "account_status IN ('active', 'disabled')",
            name="ck_registration_account_status",
        ),
        UniqueConstraint(
            "organization_id",
            "email",
            name="uq_employee_registration_email_org",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_registration_requests_branch_organization",
        ),
        ForeignKeyConstraint(
            ["department_id", "branch_id"],
            ["departments.id", "departments.branch_id"],
            name="fk_registration_requests_department_branch",
        ),
        ForeignKeyConstraint(
            ["registration_code_id", "organization_id"],
            [
                "organization_registration_codes.id",
                "organization_registration_codes.organization_id",
            ],
            name="fk_registration_requests_code_organization",
        ),
        ForeignKeyConstraint(
            ["approved_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_registration_requests_approver_organization",
        ),
        ForeignKeyConstraint(
            ["rejected_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_registration_requests_rejector_organization",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    branch_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    department_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    job_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    registration_code_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    verification_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    email_verification_status: Mapped[str] = mapped_column(
        String(20),
        default="unverified",
        nullable=False,
    )
    verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    account_status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
    )
    approval_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    approved_by_user_id: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    rejected_by_user_id: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
