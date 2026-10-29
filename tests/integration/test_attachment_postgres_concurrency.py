"""CI-only races on a disposable PostgreSQL service. Immutable audit rows are retained."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker
from app.models.organization import Organization
from app.models.user import User
from app.models.message import Message
from app.models.attachment import Attachment
from app.services.messaging_service import create_group_conversation, send_message
from app.services.attachment_service import reserve, finish, AttachmentConflict
from app.core.config import settings


@pytest.mark.skipif(
    os.getenv("NEXAWORK_TEST_POSTGRES_CONCURRENCY") != "1",
    reason="Disposable PostgreSQL integration is opt-in",
)
def test_competing_attachment_claims_commit_one_complete_message(monkeypatch):
    if not (os.getenv("GITHUB_ACTIONS") == "true" and os.getenv("DB_HOST") in {"localhost", "127.0.0.1", "::1"}
            and os.getenv("DB_NAME") == "nexawork_migration_test" and os.getenv("DB_USER") == "nexawork_test"):
        pytest.fail("Safety stop: this commits immutable audit rows; use the disposable CI PostgreSQL service only")
    monkeypatch.setattr(settings, "attachments_enabled", True)
    engine = create_engine(URL.create("postgresql+psycopg", username=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", "5432")), database=os.environ["DB_NAME"]))
    factory = sessionmaker(engine, autoflush=False, expire_on_commit=False)
    marker = uuid4().hex
    try:
        with factory() as db:
            org = Organization(name="Attachment race test", slug=f"attachment-race-{marker}")
            db.add(org); db.flush()
            user = User(
                organization_id=org.id,
                email=f"attachment-race-{marker}@example.invalid",
                full_name="Race Test",
                password_hash="test-only",
                is_active=True,
                is_super_admin=False,
            )
            db.add(user);db.commit()
            group = create_group_conversation(db, org.id, user.id, "Race", [user.id])
            draft = reserve(db, org.id, group.id, user.id, "notes.txt")
            finish(db, org.id, group.id, user.id, draft.id, 5, "a" * 64, "text/plain")
            org_id, uid, cid, aid = org.id, user.id, group.id, draft.id
        barrier = threading.Barrier(2)
        original_flush = Session.flush
        def flush(session, *args, **kwargs):
            synchronize = any(isinstance(
                row,
                Message,
            ) for row in session.new) and not session.info.get("race_synchronized")
            original_flush(session, *args, **kwargs)
            if synchronize:
                session.info["race_synchronized"] = True
                barrier.wait(timeout=15)
        monkeypatch.setattr(Session, "flush", flush)
        def send():
            with factory() as db:
                try:
                    return send_message(db, org_id, cid, uid, "One winning claim", [aid], str(uuid4())).id
                except AttachmentConflict:
                    return None
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(send), executor.submit(send)]
            results = [future.result(timeout=30) for future in futures]
        assert sum(result is not None for result in results) == 1
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(Message).where(Message.organization_id == org_id)) == 1
            attachment = db.get(Attachment, aid)
            assert attachment.status == "attached" and attachment.message_id in results
    finally:
        # Never delete immutable audit rows to clean up a test. CI discards the service.
        engine.dispose()
