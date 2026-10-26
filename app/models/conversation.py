from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    __table_args__ = (
        UniqueConstraint(
            "id",
            "organization_id",
            name="uq_conversations_id_organization",
        ),
        UniqueConstraint(
            "organization_id",
            "direct_user_low_id",
            "direct_user_high_id",
            name="uq_conversations_direct_pair",
        ),
        ForeignKeyConstraint(
            ["created_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_conversations_creator_organization",
        ),
        ForeignKeyConstraint(
            ["direct_user_low_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_conversations_direct_low_organization",
        ),
        ForeignKeyConstraint(
            ["direct_user_high_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_conversations_direct_high_organization",
        ),
        CheckConstraint(
            """
            (
                conversation_type = 'direct'
                AND direct_user_low_id IS NOT NULL
                AND direct_user_high_id IS NOT NULL
                AND direct_user_low_id < direct_user_high_id
                AND name IS NULL
            )
            OR
            (
                conversation_type = 'group'
                AND direct_user_low_id IS NULL
                AND direct_user_high_id IS NULL
                AND name IS NOT NULL
                AND length(trim(name)) > 0
            )
            """,
            name="ck_conversations_type_and_participants",
        ),
        Index(
            "ix_conversations_organization_created",
            "organization_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
    )

    conversation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    direct_user_low_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    direct_user_high_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
