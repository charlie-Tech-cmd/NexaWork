"""Protect audited user identity scope and serialize audit writes.

Revision ID: f6a31c8d9e20
Revises: d4e8f1a9c603
"""

from alembic import op


revision = "f6a31c8d9e20"
down_revision = "d4e8f1a9c603"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.enforce_audit_log_actor_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            actor_org_id INTEGER;
            actor_is_super_admin BOOLEAN;
        BEGIN
            SELECT organization_id, is_super_admin
            INTO actor_org_id, actor_is_super_admin
            FROM users
            WHERE id = NEW.user_id
            FOR UPDATE;

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
        $function$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.prevent_audited_user_identity_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF (
                OLD.organization_id IS DISTINCT FROM NEW.organization_id
                OR OLD.is_super_admin IS DISTINCT FROM NEW.is_super_admin
            ) AND EXISTS (
                SELECT 1
                FROM audit_logs
                WHERE user_id = OLD.id
            ) THEN
                RAISE EXCEPTION
                    'cannot change identity scope after audit records exist';
            END IF;

            RETURN NEW;
        END;
        $function$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_users_protect_audited_identity
        BEFORE UPDATE OF organization_id, is_super_admin ON users
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_audited_user_identity_change();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_users_protect_audited_identity
        ON users;
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS public.prevent_audited_user_identity_change();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.enforce_audit_log_actor_scope()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
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
        $function$;
        """
    )
