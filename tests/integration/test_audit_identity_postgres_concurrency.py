"""Opt-in PostgreSQL concurrency tests for audited user identity scope."""

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import create_engine, delete, text, update
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User


@pytest.mark.skipif(
    os.getenv("NEXAWORK_TEST_POSTGRES_CONCURRENCY") != "1",
    reason="Set NEXAWORK_TEST_POSTGRES_CONCURRENCY=1 to run PostgreSQL integration tests",
)
def test_identity_change_cannot_race_with_new_audit_record():
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.fail(
            "Missing required local test database environment variables: "
            + ", ".join(missing)
        )

    if os.environ["DB_HOST"] not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Safety stop: DB_HOST must be local.")
    if os.environ["DB_NAME"] != "nexawork_migration_test":
        pytest.fail("Safety stop: unexpected database name.")
    if os.environ["DB_USER"] != "nexawork_test":
        pytest.fail("Safety stop: unexpected database user.")

    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )
    engine = create_engine(url, pool_size=5, max_overflow=0)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    marker = uuid.uuid4().hex
    organization_id = None
    user_id = None
    app_name = f"audit-race-{marker}"[:63]
    update_started = Event()
    update_result = {}

    try:
        with session_factory() as db:
            organization = Organization(
                name=f"Audit race test {marker}",
                slug=f"audit-race-{marker}",
            )
            db.add(organization)
            db.flush()
            organization_id = organization.id

            user = User(
                organization_id=organization_id,
                email=f"audit-race-{marker}@example.invalid",
                password_hash="test-only-not-a-real-password-hash",
                full_name="Audit Race Test User",
                is_active=True,
                is_super_admin=False,
            )
            db.add(user)
            db.commit()
            user_id = user.id

        def change_identity():
            with session_factory() as db:
                db.execute(
                    text("SELECT set_config('application_name', :name, false)"),
                    {"name": app_name},
                )
                update_started.set()
                try:
                    db.execute(
                        update(User)
                        .where(User.id == user_id)
                        .values(
                            is_super_admin=True,
                            organization_id=None,
                        )
                    )
                    db.commit()
                    update_result["rejected"] = False
                except Exception as exc:
                    db.rollback()
                    update_result["rejected"] = (
                        "cannot change identity scope after audit records exist"
                        in str(exc)
                    )
                    update_result["error"] = str(exc)

        with session_factory() as audit_db:
            # Hold the actor row so the competing UPDATE must wait.
            audit_db.execute(
                text("SELECT id FROM users WHERE id = :user_id FOR UPDATE"),
                {"user_id": user_id},
            )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(change_identity)
                started = update_started.wait(timeout=10)
                blocked = False

                if started:
                    # Wait until PostgreSQL confirms the UPDATE is blocked.
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        blocked = bool(
                            audit_db.execute(
                                text("""
                                    SELECT EXISTS (
                                        SELECT 1
                                        FROM pg_stat_activity
                                        WHERE application_name = :app_name
                                          AND wait_event_type = 'Lock'
                                    )
                                """),
                                {"app_name": app_name},
                            ).scalar_one()
                        )
                        if blocked:
                            break
                        time.sleep(0.05)

                if not started or not blocked:
                    # Release the row lock before waiting for the worker.
                    audit_db.rollback()
                    future.result(timeout=15)
                    pytest.fail(
                        "Identity update did not start and block on the "
                        "expected PostgreSQL row lock."
                    )

                audit_db.add(
                    AuditLog(
                        organization_id=organization_id,
                        user_id=user_id,
                        actor_organization_id=organization_id,
                        action="USER_UPDATE",
                        resource_type="user",
                        resource_id=user_id,
                    )
                )
                audit_db.commit()
                future.result(timeout=15)

        expected_error = (
            "cannot change identity scope after audit records exist"
        )
        assert update_result.get("rejected") is True, (
            "Identity update failed for an unexpected reason: "
            f"{update_result.get('error', 'no error recorded')}"
        )
        assert expected_error in update_result.get("error", ""), (
            "Identity update was rejected, but not by the expected "
            "identity-protection trigger. Actual error: "
            f"{update_result.get('error', 'no error recorded')}"
        )

        with session_factory() as db:
            saved_user = db.get(User, user_id)
            assert saved_user is not None
            assert saved_user.is_super_admin is False
            assert saved_user.organization_id == organization_id
            assert db.query(AuditLog).filter_by(user_id=user_id).count() == 1

    finally:
        with session_factory() as db:
            if user_id is not None:
                db.execute(delete(AuditLog).where(AuditLog.user_id == user_id))
                db.execute(delete(User).where(User.id == user_id))
            if organization_id is not None:
                db.execute(
                    delete(Organization).where(
                        Organization.id == organization_id
                    )
                )
            db.commit()
        engine.dispose()
