from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmployeeInvitation(Base):
    __tablename__ = "employee_invitations"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked', 'expired')",
            name="ck_employee_invitation_status",
        ),
        Index(
            "uq_employee_invitation_pending_email_org",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
        ForeignKeyConstraint(
            ["created_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_employee_invitations_creator_organization",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_employee_invitations_branch_organization",
        ),
        ForeignKeyConstraint(
            ["department_id", "branch_id"],
            ["departments.id", "departments.branch_id"],
            name="fk_employee_invitations_department_branch",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
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
    invitation_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
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
