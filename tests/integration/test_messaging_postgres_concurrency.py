"""Opt-in PostgreSQL concurrency regression test for direct messaging."""

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.organization import Organization
from app.models.user import User
import app.services.messaging_service as messaging


@pytest.mark.skipif(
    os.getenv("NEXAWORK_TEST_POSTGRES_CONCURRENCY") != "1",
    reason="Set NEXAWORK_TEST_POSTGRES_CONCURRENCY=1 to run PostgreSQL integration tests",
)
def test_concurrent_direct_creation_recovers_from_unique_conflict(monkeypatch):
    """Two sessions racing to create one pair must converge on one conversation."""
    required = (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )
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
    user_ids = []
    initial_lookup_barrier = threading.Barrier(2)
    observed_conflicts = []
    conflict_lock = threading.Lock()

    original_scalar = Session.scalar
    original_detector = messaging._is_direct_pair_unique_violation

    def synchronized_scalar(session, statement, *args, **kwargs):
        result = original_scalar(session, statement, *args, **kwargs)
        descriptions = getattr(statement, "column_descriptions", ())
        is_conversation_query = (
            bool(descriptions)
            and descriptions[0].get("entity") is Conversation
        )

        if is_conversation_query and result is None:
            initial_lookup_barrier.wait(timeout=15)

        return result

    def observe_unique_conflict(exc):
        matched = original_detector(exc)
        if matched:
            with conflict_lock:
                observed_conflicts.append(True)
        return matched

    try:
        # Use fresh, uniquely named records owned exclusively by this test.
        with session_factory() as db:
            organization = Organization(
                name=f"Messaging concurrency test {marker}",
                slug=f"msg-concurrency-{marker}",
            )
            db.add(organization)
            db.flush()
            organization_id = organization.id

            users = [
                User(
                    organization_id=organization_id,
                    email=f"msg-concurrency-{marker}-{number}@example.invalid",
                    password_hash="test-only-not-a-real-password-hash",
                    full_name=f"Messaging Test User {number}",
                    is_active=True,
                    is_super_admin=False,
                )
                for number in (1, 2)
            ]
            db.add_all(users)
            db.commit()
            user_ids = [user.id for user in users]

        # Synchronize the initial lookup and observe the exact recovery branch.
        monkeypatch.setattr(Session, "scalar", synchronized_scalar)
        monkeypatch.setattr(
            messaging, "_is_direct_pair_unique_violation", observe_unique_conflict
        )

        def create_direct():
            with session_factory() as db:
                conversation = messaging.create_or_get_direct_conversation(
                    db, organization_id, user_ids[0], user_ids[1]
                )
                return conversation.id

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(create_direct),
                executor.submit(create_direct),
            ]
            conversation_ids = [future.result(timeout=30) for future in futures]

        assert conversation_ids[0] == conversation_ids[1]
        assert observed_conflicts, (
            "The direct-pair uniqueness-conflict recovery branch was not exercised."
        )

        with session_factory() as db:
            active_member_ids = set(
                db.scalars(
                    select(ConversationMember.user_id).where(
                        ConversationMember.organization_id == organization_id,
                        ConversationMember.conversation_id == conversation_ids[0],
                        ConversationMember.is_active.is_(True),
                    )
                ).all()
            )

            direct_pair_ids = db.scalars(
                select(Conversation.id).where(
                    Conversation.organization_id == organization_id,
                    Conversation.direct_user_low_id == min(user_ids),
                    Conversation.direct_user_high_id == max(user_ids),
                )
            ).all()

        assert active_member_ids == set(user_ids)
        assert len(direct_pair_ids) == 1, (
            "Concurrent requests must leave exactly one direct conversation "
            "for this organization and user pair."
        )

    finally:
        # Restore instrumentation before cleaning up test data.
        monkeypatch.setattr(Session, "scalar", original_scalar)
        monkeypatch.setattr(
            messaging, "_is_direct_pair_unique_violation", original_detector
        )

        if organization_id is not None:
            with session_factory() as db:
                db.execute(
                    delete(Message).where(
                        Message.organization_id == organization_id
                    )
                )
                db.execute(
                    delete(ConversationMember).where(
                        ConversationMember.organization_id == organization_id
                    )
                )
                db.execute(
                    delete(Conversation).where(
                        Conversation.organization_id == organization_id
                    )
                )
                if user_ids:
                    db.execute(delete(User).where(User.id.in_(user_ids)))
                db.execute(
                    delete(Organization).where(
                        Organization.id == organization_id
                    )
                )
                db.commit()

        engine.dispose()
