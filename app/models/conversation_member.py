from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConversationMember(Base):
    __tablename__ = "conversation_members"

    __table_args__ = (
        CheckConstraint(
            "role IN ('member', 'admin')",
            name="ck_conversation_members_role",
        ),
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_members_conversation_user",
        ),
        ForeignKeyConstraint(
            ["conversation_id", "organization_id"],
            ["conversations.id", "conversations.organization_id"],
            name="fk_conversation_members_conversation_organization",
        ),
        ForeignKeyConstraint(
            ["user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_conversation_members_user_organization",
        ),
        Index(
            "ix_conversation_members_organization_user",
            "organization_id",
            "user_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(nullable=False)

    organization_id: Mapped[int] = mapped_column(nullable=False)

    user_id: Mapped[int] = mapped_column(nullable=False)

    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
