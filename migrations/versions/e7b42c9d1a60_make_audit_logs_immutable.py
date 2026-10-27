"""Prevent updates and deletions of audit log records.

Revision ID: e7b42c9d1a60
Revises: f6a31c8d9e20
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e7b42c9d1a60"
down_revision: Union[str, Sequence[str], None] = "f6a31c8d9e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Reject attempts to modify or delete existing audit records."""

    op.execute(
        """
        CREATE FUNCTION public.prevent_audit_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION
                'audit log records are immutable'
                USING ERRCODE = '55000';
        END;
        $function$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_prevent_update_delete
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_audit_log_mutation();
        """
    )


def downgrade() -> None:
    """Remove the audit-record immutability protection."""

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_audit_logs_prevent_update_delete
        ON audit_logs;
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS public.prevent_audit_log_mutation();
        """
    )
