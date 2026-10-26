"""Enforce audit log actor and organization scope.

Revision ID: c29a4f1d7e62
Revises: 8582f542826e
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "c29a4f1d7e62"
down_revision: Union[str, Sequence[str], None] = "8582f542826e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enforce audit actor scope while preserving Super Admin auditing."""

    # Refuse to migrate existing tenant audit records that cross organization
    # boundaries. Super Admin actions against customer organizations are valid.
    if not context.is_offline_mode():
        connection = op.get_bind()
        invalid_count = connection.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM audit_logs AS a
                JOIN users AS u ON u.id = a.user_id
                WHERE u.is_super_admin = FALSE
                  AND (
                      u.organization_id IS NULL
                      OR a.organization_id IS DISTINCT FROM u.organization_id
                  )
                """
            )
        ).scalar_one()

        if invalid_count:
            raise RuntimeError(
                "Cannot enforce audit actor scope: found "
                f"{invalid_count} audit log record(s) where a tenant actor "
                "belongs to a different organization. Review and reconcile "
                "these records before retrying the migration."
            )

    # NULL is reserved for Super Admin actors, who have no tenant organization.
    op.add_column(
        "audit_logs",
        sa.Column("actor_organization_id", sa.Integer(), nullable=True),
    )

    # Backfill existing tenant records from the actor's actual organization.
    # Super Admin rows intentionally remain NULL.
    op.execute(
        """
        UPDATE audit_logs AS a
        SET actor_organization_id = u.organization_id
        FROM users AS u
        WHERE a.user_id = u.id
          AND u.is_super_admin = FALSE
        """
    )

    # The single-column user FK remains in place. This composite FK additionally
    # validates tenant actor organization membership; NULL permits Super Admins.
    op.create_foreign_key(
        "fk_audit_logs_actor_organization",
        "audit_logs",
        "users",
        ["user_id", "actor_organization_id"],
        ["id", "organization_id"],
    )

    op.execute(
        """
        CREATE FUNCTION enforce_audit_log_actor_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            actor_org_id INTEGER;
            actor_is_super_admin BOOLEAN;
        BEGIN
            SELECT organization_id, is_super_admin
            INTO actor_org_id, actor_is_super_admin
            FROM users
            WHERE id = NEW.user_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'audit actor does not exist';
            END IF;

            IF actor_is_super_admin THEN
                IF NEW.actor_organization_id IS NOT NULL THEN
                    RAISE EXCEPTION
                        'Super Admin actor organization must be NULL';
                END IF;
            ELSE
                IF NEW.actor_organization_id IS DISTINCT FROM actor_org_id
                   OR NEW.organization_id IS DISTINCT FROM actor_org_id THEN
                    RAISE EXCEPTION
                        'audit actor organization does not match target organization';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_actor_scope
        BEFORE INSERT OR UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION enforce_audit_log_actor_scope()
        """
    )



def downgrade() -> None:
    """Remove the actor-scope enforcement."""

    op.execute(
        "DROP TRIGGER IF EXISTS trg_audit_logs_actor_scope ON audit_logs"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_audit_log_actor_scope()")

    op.drop_constraint(
        "fk_audit_logs_actor_organization",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_column("audit_logs", "actor_organization_id")
