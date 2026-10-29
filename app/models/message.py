from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        UniqueConstraint("id", "conversation_id", "organization_id", name="uq_messages_scope"),
        UniqueConstraint(
            "organization_id",
            "conversation_id",
            "sender_id",
            "client_message_id",
            name="uq_messages_client_request",
        ),
        ForeignKeyConstraint(
            ["conversation_id", "organization_id"],
            ["conversations.id", "conversations.organization_id"],
            name="fk_messages_conversation_organization",
        ),
        ForeignKeyConstraint(
            ["sender_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_messages_sender_organization",
        ),
        CheckConstraint(
            "length(trim(body)) > 0",
            name="ck_messages_body_not_empty",
        ),
        Index(
            "ix_messages_conversation_id_id",
            "conversation_id",
            "id",
        ),
        Index(
            "ix_messages_organization_sender",
            "organization_id",
            "sender_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(nullable=False)

    organization_id: Mapped[int] = mapped_column(nullable=False)

    sender_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    client_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
