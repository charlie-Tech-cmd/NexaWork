"""Private attachment metadata and idempotent message requests.

Revision ID: ab921ed70431
Revises: e7b42c9d1a60
"""
from alembic import op
import sqlalchemy as sa

revision = "ab921ed70431"
down_revision = "e7b42c9d1a60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_messages_scope", "messages", ["id", "conversation_id", "organization_id"])
    op.add_column("messages", sa.Column("client_message_id", sa.String(36), nullable=True))
    op.add_column("messages", sa.Column("request_hash", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_messages_client_request",
        "messages",
        ["organization_id", "conversation_id", "sender_id", "client_message_id"],
    )
    op.create_table("attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.String(64), nullable=False, unique=True),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id", "organization_id"],
            ["conversations.id", "conversations.organization_id"],
        ),
        sa.ForeignKeyConstraint(["uploaded_by_user_id", "organization_id"], ["users.id", "users.organization_id"]),
        sa.ForeignKeyConstraint(
            ["message_id", "conversation_id", "organization_id"],
            ["messages.id", "messages.conversation_id", "messages.organization_id"],
        ),
        sa.CheckConstraint(
            "status IN ('uploading','ready','attached','deleting','deleted')",
            name="ck_attachments_status",
        ),
        sa.CheckConstraint(
            "status NOT IN ('ready','attached') OR (size_bytes > 0 AND sha256 IS NOT NULL)",
            name="ck_attachments_complete",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_attachments_size"),
        sa.CheckConstraint("status != 'attached' OR message_id IS NOT NULL", name="ck_attachments_attached"),
        sa.CheckConstraint(
            "status NOT IN ('uploading','ready') OR message_id IS NULL",
            name="ck_attachments_draft",
        ))
    op.create_index(
        "ix_attachments_conversation_page",
        "attachments",
        ["organization_id", "conversation_id", "id"],
    )
    op.create_index("ix_attachments_message", "attachments", ["message_id", "id"])
    op.create_index("ix_attachments_cleanup", "attachments", ["status", "expires_at"])


def downgrade():
    # Destructive after files exist; operators must preserve metadata and objects first.
    op.drop_table("attachments")
    op.drop_constraint("uq_messages_client_request", "messages", type_="unique")
    op.drop_column("messages", "request_hash")
    op.drop_column("messages", "client_message_id")
    op.drop_constraint("uq_messages_scope", "messages", type_="unique")
