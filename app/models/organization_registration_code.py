from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationRegistrationCode(Base):
    __tablename__ = "organization_registration_codes"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            name="uq_organization_registration_code",
        ),
        UniqueConstraint(
            "id",
            "organization_id",
            name="uq_registration_codes_id_organization",
        ),
        ForeignKeyConstraint(
            ["created_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_registration_codes_creator_organization",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
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
