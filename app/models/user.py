from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DDL,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    event,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index(
            "ix_users_org_lifecycle_approval_created",
            "organization_id",
            "lifecycle_managed",
            "approval_status",
            "created_at",
            "id",
        ),
        UniqueConstraint(
            "id",
            "organization_id",
            name="uq_users_id_organization",
        ),
        CheckConstraint(
            """
            (
                is_super_admin = FALSE
                AND organization_id IS NOT NULL
            )
            OR
            (
                is_super_admin = TRUE
                AND organization_id IS NULL
            )
            """,
            name="ck_users_super_admin_organization",
        ),
        CheckConstraint(
            """
            approval_status IN ('pending', 'approved', 'rejected')
            AND (
                lifecycle_managed = TRUE
                OR approval_status = 'approved'
            )
            """,
            name="ck_users_approval_status",
        ),
        CheckConstraint(
            """
            lifecycle_managed = FALSE
            OR (
                is_super_admin = FALSE
                AND organization_id IS NOT NULL
            )
            """,
            name="ck_users_lifecycle_managed_tenant",
        ),
        CheckConstraint(
            """
            lifecycle_managed = FALSE
            OR is_active = FALSE
            OR (
                approval_status = 'approved'
                AND email_verified_at IS NOT NULL
            )
            """,
            name="ck_users_lifecycle_active_eligible",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    lifecycle_managed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_status: Mapped[str] = mapped_column(
        String(16),
        default="approved",
        nullable=False,
    )
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    token_version: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


event.listen(
    User.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER trg_users_protect_audited_identity
        BEFORE UPDATE OF organization_id, is_super_admin ON users
        WHEN (
            OLD.organization_id IS NOT NEW.organization_id
            OR OLD.is_super_admin IS NOT NEW.is_super_admin
        )
        AND EXISTS (
            SELECT 1
            FROM audit_logs
            WHERE user_id = OLD.id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'cannot change identity scope after audit records exist'
            );
        END;
        """
    ).execute_if(dialect="sqlite"),
)
