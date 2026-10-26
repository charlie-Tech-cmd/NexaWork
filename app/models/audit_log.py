from datetime import datetime, timezone

from sqlalchemy import (
    DDL,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "actor_organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_audit_logs_actor_organization",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Organization whose resources or actions are being audited.
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    # User who performed the action.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Null only for a Super Admin, who has no tenant organization.
    actor_organization_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER trg_audit_logs_actor_scope
        BEFORE INSERT ON audit_logs
        BEGIN
            SELECT CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM users WHERE id = NEW.user_id
                )
                THEN RAISE(ABORT, 'audit actor does not exist')

                WHEN (
                    SELECT is_super_admin FROM users
                    WHERE id = NEW.user_id
                ) = 1
                AND NEW.actor_organization_id IS NOT NULL
                THEN RAISE(ABORT, 'super admin actor organization must be null')

                WHEN (
                    SELECT is_super_admin FROM users
                    WHERE id = NEW.user_id
                ) = 0
                AND (
                    NEW.actor_organization_id IS NULL
                    OR NEW.actor_organization_id != (
                        SELECT organization_id FROM users
                        WHERE id = NEW.user_id
                    )
                    OR NEW.organization_id != (
                        SELECT organization_id FROM users
                        WHERE id = NEW.user_id
                    )
                )
                THEN RAISE(ABORT, 'audit actor organization mismatch')
            END;
        END;
        """
    ).execute_if(dialect="sqlite"),
)

event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER trg_audit_logs_actor_scope_update
        BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM users WHERE id = NEW.user_id
                )
                THEN RAISE(ABORT, 'audit actor does not exist')

                WHEN (
                    SELECT is_super_admin FROM users
                    WHERE id = NEW.user_id
                ) = 1
                AND NEW.actor_organization_id IS NOT NULL
                THEN RAISE(ABORT, 'super admin actor organization must be null')

                WHEN (
                    SELECT is_super_admin FROM users
                    WHERE id = NEW.user_id
                ) = 0
                AND (
                    NEW.actor_organization_id IS NULL
                    OR NEW.actor_organization_id != (
                        SELECT organization_id FROM users
                        WHERE id = NEW.user_id
                    )
                    OR NEW.organization_id != (
                        SELECT organization_id FROM users
                        WHERE id = NEW.user_id
                    )
                )
                THEN RAISE(ABORT, 'audit actor organization mismatch')
            END;
        END;
        """
    ).execute_if(dialect="sqlite"),
)
