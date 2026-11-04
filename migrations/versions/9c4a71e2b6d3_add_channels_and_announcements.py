"""Add persistent channels and organization announcements."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4a71e2b6d3"
down_revision: Union[str, Sequence[str], None] = "f00b3e22a91c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("channel_visibility", sa.String(length=10), nullable=True),
    )
    op.drop_constraint(
        "ck_conversations_type_and_participants",
        "conversations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_conversations_type_and_participants",
        "conversations",
        """
        (
            conversation_type = 'direct'
            AND direct_user_low_id IS NOT NULL
            AND direct_user_high_id IS NOT NULL
            AND direct_user_low_id < direct_user_high_id
            AND name IS NULL
            AND channel_visibility IS NULL
        )
        OR
        (
            conversation_type = 'group'
            AND direct_user_low_id IS NULL
            AND direct_user_high_id IS NULL
            AND name IS NOT NULL
            AND length(trim(name)) > 0
            AND channel_visibility IS NULL
        )
        OR
        (
            conversation_type = 'channel'
            AND direct_user_low_id IS NULL
            AND direct_user_high_id IS NULL
            AND name IS NOT NULL
            AND length(trim(name)) > 0
            AND channel_visibility IN ('public', 'private')
        )
        """,
    )
    op.create_index(
        "uq_conversations_channel_name",
        "conversations",
        ["organization_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("conversation_type = 'channel'"),
        sqlite_where=sa.text("conversation_type = 'channel'"),
    )
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_announcements_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_announcements_author_organization",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_announcements_organization_created",
        "announcements",
        ["organization_id", "created_at", "id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO permissions (name, description, is_active, created_at)
            SELECT seeded.name, seeded.description, TRUE, NOW()
            FROM (
                SELECT 'CHANNEL_CREATE' AS name, 'Create workplace channels' AS description
                UNION ALL
                SELECT 'ANNOUNCEMENT_CREATE', 'Publish organization announcements'
            ) AS seeded
            WHERE NOT EXISTS (
                SELECT 1
                FROM permissions AS existing
                WHERE existing.name = seeded.name
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT DISTINCT role.id, permission.id
            FROM roles AS role
            CROSS JOIN permissions AS permission
            WHERE role.name = 'Organization Admin'
              AND role.is_active = TRUE
              AND permission.name IN ('CHANNEL_CREATE', 'ANNOUNCEMENT_CREATE')
              AND permission.is_active = TRUE
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions AS existing
                  WHERE existing.role_id = role.id
                    AND existing.permission_id = permission.id
              )
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_channel_data = connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM conversations "
            "WHERE conversation_type = 'channel')"
        )
    )
    has_announcement_data = connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM announcements)")
    )
    if has_channel_data or has_announcement_data:
        raise RuntimeError(
            "Cannot downgrade while channels or announcements contain data"
        )

    op.drop_index(
        "ix_announcements_organization_created",
        table_name="announcements",
    )
    op.drop_table("announcements")
    op.drop_index(
        "uq_conversations_channel_name",
        table_name="conversations",
    )
    op.drop_constraint(
        "ck_conversations_type_and_participants",
        "conversations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_conversations_type_and_participants",
        "conversations",
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
    )
    op.drop_column("conversations", "channel_visibility")
