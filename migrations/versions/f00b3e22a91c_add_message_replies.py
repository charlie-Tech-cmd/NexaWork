"""add conversation-scoped message replies

Revision ID: f00b3e22a91c
Revises: ab921ed70431
"""
from alembic import op
import sqlalchemy as sa


revision = "f00b3e22a91c"
down_revision = "ab921ed70431"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "messages",
        sa.Column("reply_to_message_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_reply_scope",
        "messages",
        "messages",
        ["reply_to_message_id", "conversation_id", "organization_id"],
        ["id", "conversation_id", "organization_id"],
    )


def downgrade():
    op.drop_constraint("fk_messages_reply_scope", "messages", type_="foreignkey")
    op.drop_column("messages", "reply_to_message_id")
