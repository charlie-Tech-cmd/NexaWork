"""Verify the Organization Admin team-permission migration on PostgreSQL."""

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def get_engine():
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
    )
    return create_engine(url)


def seed(connection):
    fixtures = [
        ("ci-team-permission-test-a", True),
        ("ci-team-permission-test-b", True),
        ("ci-team-permission-test-inactive", False),
    ]

    role_ids = {}

    for slug, active in fixtures:
        organization_id = connection.execute(
            text("""
                INSERT INTO organizations
                    (name, slug, is_active, created_at, updated_at)
                VALUES
                    (:name, :slug, TRUE, NOW(), NOW())
                RETURNING id
            """),
            {"name": slug, "slug": slug},
        ).scalar_one()

        role_ids[slug] = connection.execute(
            text("""
                INSERT INTO roles
                    (organization_id, name, is_active, created_at)
                VALUES
                    (:organization_id, 'Organization Admin', :active, NOW())
                RETURNING id
            """),
            {"organization_id": organization_id, "active": active},
        ).scalar_one()

    # Preserve a pre-existing grant and ensure the migration doesn't duplicate it.
    result = connection.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT :role_id, id
            FROM permissions
            WHERE name = 'TEAM_VIEW'
        """),
        {"role_id": role_ids["ci-team-permission-test-a"]},
    )

    if result.rowcount != 1:
        raise RuntimeError(
            "Expected exactly one TEAM_VIEW permission to exist before migration."
        )

    print("Seeded two active roles, one inactive role, and one existing grant.")


def check(connection):
    expected = {"TEAM_VIEW", "TEAM_CREATE", "TEAM_UPDATE"}

    for slug in (
        "ci-team-permission-test-a",
        "ci-team-permission-test-b",
    ):

        names = set(connection.execute(
            text("""
                SELECT p.name
                FROM roles r
                JOIN role_permissions rp ON rp.role_id = r.id
                JOIN permissions p ON p.id = rp.permission_id
                JOIN organizations o ON o.id = r.organization_id
                WHERE o.slug = :slug
                  AND r.name = 'Organization Admin'
            """),
            {"slug": slug},
        ).scalars())

        missing = expected - names
        assert not missing, (
            f"{slug}: missing team permissions {missing}; "
            f"found permissions {names}"
        )

    inactive_count = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM roles r
            JOIN organizations o ON o.id = r.organization_id
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE o.slug = 'ci-team-permission-test-inactive'
              AND r.name = 'Organization Admin'
              AND p.name IN ('TEAM_VIEW', 'TEAM_CREATE', 'TEAM_UPDATE')
        """)
    ).scalar_one()

    assert inactive_count == 0, (
        f"Inactive role unexpectedly received {inactive_count} team grants"
    )

    print("PASS: both active organizations have all three team permissions.")
    print("PASS: inactive Organization Admin received no team permissions.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"seed", "check"}:
        raise SystemExit("Usage: python scripts/verify_team_permission_migration.py seed|check")

    engine = get_engine()
    try:
        with engine.begin() as connection:
            if sys.argv[1] == "seed":
                seed(connection)
            else:
                check(connection)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
