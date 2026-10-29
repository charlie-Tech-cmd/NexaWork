from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        ForeignKeyConstraint(["conversation_id", "organization_id"],
                             ["conversations.id", "conversations.organization_id"]),
        ForeignKeyConstraint(["uploaded_by_user_id", "organization_id"],
                             ["users.id", "users.organization_id"]),
        ForeignKeyConstraint(["message_id", "conversation_id", "organization_id"],
                             ["messages.id", "messages.conversation_id", "messages.organization_id"]),
        CheckConstraint("status IN ('uploading','ready','attached','deleting','deleted')",
                        name="ck_attachments_status"),
        CheckConstraint(
            "status NOT IN ('ready','attached') OR (size_bytes > 0 AND sha256 IS NOT NULL)",
            name="ck_attachments_complete",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_attachments_size"),
        CheckConstraint("status != 'attached' OR message_id IS NOT NULL", name="ck_attachments_attached"),
        CheckConstraint("status NOT IN ('uploading','ready') OR message_id IS NULL", name="ck_attachments_draft"),
        Index("ix_attachments_conversation_page", "organization_id", "conversation_id", "id"),
        Index("ix_attachments_message", "message_id", "id"),
        Index("ix_attachments_cleanup", "status", "expires_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(nullable=False)
    conversation_id: Mapped[int] = mapped_column(nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(nullable=False)
    message_id: Mapped[int | None] = mapped_column(nullable=True)
    storage_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(default=0, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="uploading", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
