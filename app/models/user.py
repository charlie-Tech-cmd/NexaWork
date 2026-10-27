from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DDL,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    event,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
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
