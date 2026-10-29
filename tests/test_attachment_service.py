from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.message import Message
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User
from app.models.conversation_member import ConversationMember
from app.services import attachment_service as files
from app.services.messaging_service import create_group_conversation, send_message, ConversationAccessError
from app.workers.attachment_cleanup import cleanup
from app.integrations.storage.local import LocalStorage


@pytest.fixture
def data(db_session, organization, monkeypatch):
    monkeypatch.setattr(settings, "attachments_enabled", True)
    users = [User(
        organization_id=organization.id,
        email=f"file-svc-{i}@example.com",
        full_name=f"Member {i}",
        password_hash="test-only",
        is_active=True,
        is_super_admin=False,
    ) for i in range(3)]
    db_session.add_all(users); db_session.commit()
    conversation = create_group_conversation(db_session, organization.id, users[0].id, "Work", [users[1].id])
    return organization.id, users, conversation.id


def ready(db, org, cid, uid):
    item = files.reserve(db, org, cid, uid, "notes.txt")
    return files.finish(db, org, cid, uid, item.id, 5, "a" * 64, "text/plain")


def test_binding_and_retry_are_atomic_and_audited(db_session, data):
    org, users, cid = data
    a = ready(db_session, org, cid, users[0].id)
    key = str(uuid4())
    first = send_message(db_session, org, cid, users[0].id, "Notes", [a.id], key)
    second = send_message(db_session, org, cid, users[0].id, "Notes", [a.id], key)
    assert first.id == second.id
    db_session.refresh(a)
    assert a.message_id == first.id and a.status == "attached"
    events = set(db_session.scalars(select(AuditLog.action).where(AuditLog.resource_id == a.id)))
    assert {"ATTACHMENT_UPLOAD", "ATTACHMENT_SHARE"}.issubset(events)
    with pytest.raises(files.AttachmentConflict):
        send_message(db_session, org, cid, users[0].id, "Different", [a.id], key)


def test_other_users_draft_and_nonmember_are_hidden(db_session, data):
    org, users, cid = data
    a = ready(db_session, org, cid, users[0].id)
    for uid in [users[1].id, users[2].id]:
        with pytest.raises(ConversationAccessError): files.get_attachment(db_session, org, cid, uid, a.id)


def test_failed_claim_rolls_back_message(db_session, data):
    org, users, cid = data
    a = ready(db_session, org, cid, users[0].id)
    with pytest.raises(ConversationAccessError):
        send_message(db_session, org, cid, users[0].id, "should rollback", [a.id, a.id + 999])
    assert db_session.scalar(select(Message).where(Message.body == "should rollback")) is None
    db_session.refresh(a)
    assert a.message_id is None and a.status == "ready"


def test_revoked_member_cannot_bind(db_session, data):
    org, users, cid = data
    a = ready(db_session, org, cid, users[0].id)
    member = db_session.scalar(select(ConversationMember).where(
        ConversationMember.conversation_id == cid,
        ConversationMember.user_id == users[0].id,
    ))
    member.is_active = False; db_session.commit()
    with pytest.raises(ConversationAccessError): send_message(
        db_session,
        org,
        cid,
        users[0].id,
        "No access",
        [a.id],
    )


def test_cleanup_preserves_attached_objects_and_retries(db_session, data, tmp_path):
    org, users, cid = data
    store = LocalStorage(str(tmp_path))
    attached = ready(db_session, org, cid, users[0].id)
    expired = ready(db_session, org, cid, users[0].id)
    for item in [attached, expired]:
        with store.create(item.storage_key) as stream: stream.write(b"hello")
    send_message(db_session, org, cid, users[0].id, "Keep", [attached.id])
    expired.expires_at = datetime.now(timezone.utc) - timedelta(days=1); db_session.commit()
    assert cleanup(db_session, store) == 1
    with store.open(attached.storage_key) as stream: assert stream.read() == b"hello"
    assert not store.path(expired.storage_key).exists()
    assert cleanup(db_session, store) == 0


def test_delete_hides_immediately_but_keeps_audit_and_message_link(db_session, data):
    org, users, cid = data
    item = ready(db_session, org, cid, users[0].id)
    message = send_message(db_session, org, cid, users[0].id, "Caption", [item.id])
    with pytest.raises(PermissionError): files.request_delete(db_session, org, cid, users[1].id, item.id)
    result = files.request_delete(db_session, org, cid, users[0].id, item.id)
    assert result.status == "deleting" and result.message_id == message.id
    assert db_session.scalar(select(AuditLog.id).where(
        AuditLog.action == "ATTACHMENT_DELETE_REQUEST",
        AuditLog.resource_id == item.id,
    ))


def test_conversation_page_ties_scope_and_continuation(db_session, data):
    from app.services.messaging_service import conversation_page, MessagingValidationError
    org, users, cid = data
    conversations = [create_group_conversation(
        db_session,
        org,
        users[0].id,
        f"Paging {i}",
        [users[1].id],
    ) for i in range(102)]
    for conversation in conversations: conversation.created_at = datetime(2026,1,1,tzinfo=timezone.utc)
    db_session.commit()
    seen, cursor = [], None
    while True:
        page, cursor = conversation_page(db_session, org, users[0].id, 50, cursor)
        seen.extend(c.id for c in page)
        if not cursor: break
    assert len(seen) == 103 and len(set(seen)) == 103
    _, cursor = conversation_page(db_session, org, users[0].id, 1)
    with pytest.raises(MessagingValidationError): conversation_page(db_session, org, users[1].id, 1, cursor)
    with pytest.raises(MessagingValidationError): conversation_page(db_session, org, users[0].id, 1, "garbage")


def test_cross_organization_file_ids_are_not_accessible(db_session, data):
    org, users, cid = data
    item = ready(db_session, org, cid, users[0].id)
    other = Organization(name="Other file tenant", slug="other-file-tenant")
    db_session.add(other); db_session.flush()
    outsider = User(
        organization_id=other.id,
        email="outside-files@example.com",
        full_name="Outside",
        password_hash="test-only",
    )
    db_session.add(outsider); db_session.commit()
    for operation in [lambda: files.get_attachment(db_session, other.id, cid, outsider.id, item.id),
                      lambda: files.page(db_session, other.id, cid, outsider.id, None, 50),
                      lambda: files.request_delete(db_session, other.id, cid, outsider.id, item.id)]:
        with pytest.raises(ConversationAccessError): operation()


def test_abandoned_reservation_cannot_be_finished(db_session, data):
    org, users, cid = data
    item = files.reserve(db_session, org, cid, users[0].id, "pending.txt")
    files.abandon(db_session, org, users[0].id, item.id)
    with pytest.raises(files.AttachmentConflict):
        files.finish(db_session, org, cid, users[0].id, item.id, 5, "b" * 64, "text/plain")


def test_late_cancellation_does_not_abandon_committed_ready_upload(db_session, data):
    org, users, cid = data
    item = ready(db_session, org, cid, users[0].id)
    assert files.abandon(db_session, org, users[0].id, item.id) is False
    db_session.refresh(item)
    assert item.status == "ready" and item.size_bytes == 5
