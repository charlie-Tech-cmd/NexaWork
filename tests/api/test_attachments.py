"""API/lifecycle tests use only synthetic bytes and temporary private storage."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.message import Message
from app.models.conversation_member import ConversationMember
from app.services.messaging_service import create_group_conversation
from app.services import attachment_service
from app.integrations.storage.local import LocalStorage
from tests.api.test_messaging import make_user, login


@pytest.fixture
def file_workspace(client, db_session, organization, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_enabled", True)
    monkeypatch.setattr(settings, "storage_local_root", str(tmp_path))
    monkeypatch.setattr(settings, "allow_unscanned_development_files", True)
    monkeypatch.setattr(settings, "file_scan_host", "")
    a = make_user(db_session, organization.id, "file.owner@example.com")
    b = make_user(db_session, organization.id, "file.member@example.com")
    outsider = make_user(db_session, organization.id, "file.outsider@example.com")
    db_session.commit()
    c = create_group_conversation(db_session, organization.id, a.id, "Files", [b.id])
    return a, b, outsider, c


def upload(client, headers, cid, data=b"hello", filename="notes.txt"):
    return client.post(
        f"/api/v1/messaging/conversations/{cid}/attachments",
        headers={**headers, "X-Filename": filename, "Content-Type": "application/octet-stream"},
        content=data,
    )


def test_file_policy_matches_feature_and_upload_readiness(
    client, file_workspace, monkeypatch, tmp_path
):
    a, _, _, conversation = file_workspace
    auth = login(client, a.email)
    path = "/api/v1/messaging/file-policy"

    ready = client.get(path, headers=auth)
    assert ready.status_code == 200
    assert ready.json()["enabled"] is True
    assert ready.json()["uploads_enabled"] is True

    monkeypatch.setattr(settings, "allow_unscanned_development_files", False)
    not_scannable = client.get(path, headers=auth)
    assert not_scannable.json()["enabled"] is True
    assert not_scannable.json()["uploads_enabled"] is False
    assert (
        client.get(
            f"/api/v1/messaging/conversations/{conversation.id}/attachments",
            headers=auth,
        ).status_code
        == 200
    )
    assert upload(client, auth, conversation.id).status_code == 503

    monkeypatch.setattr(settings, "allow_unscanned_development_files", True)
    unsafe_root = tmp_path / "unsafe-files"
    unsafe_root.mkdir()
    unsafe_root.chmod(0o755)
    monkeypatch.setattr(settings, "storage_local_root", str(unsafe_root))
    storage_not_ready = client.get(path, headers=auth)
    assert storage_not_ready.json()["enabled"] is True
    assert storage_not_ready.json()["uploads_enabled"] is False
    assert upload(client, auth, conversation.id).status_code == 503

    monkeypatch.setattr(settings, "attachments_enabled", False)
    disabled = client.get(path, headers=auth)
    assert disabled.json()["enabled"] is False
    assert disabled.json()["uploads_enabled"] is False
    root = f"/api/v1/messaging/conversations/{conversation.id}/attachments"
    assert client.get(root, headers=auth).status_code == 503
    assert client.get(f"{root}/1", headers=auth).status_code == 503
    assert client.get(f"{root}/1/download", headers=auth).status_code == 503
    assert client.delete(f"{root}/1", headers=auth).status_code == 503
    assert upload(client, auth, conversation.id).status_code == 503
    assert client.get(path).status_code == 401


def test_upload_share_download_delete_and_idempotent_send(client, db_session, file_workspace):
    a, b, _, c = file_workspace
    auth, other = login(client, a.email), login(client, b.email)
    uploaded = upload(client, auth, c.id)
    assert uploaded.status_code == 201, uploaded.text
    aid = uploaded.json()["id"]
    root = f"/api/v1/messaging/conversations/{c.id}"
    assert client.get(f"{root}/attachments/{aid}", headers=other).status_code == 404
    assert client.get(f"{root}/attachments/{aid}/download", headers=auth).status_code == 409
    payload = {"body": "Review notes", "attachment_ids": [aid], "client_message_id": str(uuid4())}
    sent = client.post(f"{root}/messages", headers=auth, json=payload)
    assert sent.status_code == 201, sent.text
    replay = client.post(f"{root}/messages", headers=auth, json=payload)
    assert replay.json()["id"] == sent.json()["id"]
    assert len(sent.json()["attachments"]) == 1
    download = client.get(f"{root}/attachments/{aid}/download", headers=other)
    assert download.status_code == 200 and download.content == b"hello"
    assert "attachment;" in download.headers["content-disposition"]
    assert download.headers["cache-control"] == "private, no-store"
    assert client.delete(f"{root}/attachments/{aid}", headers=other).status_code == 403
    assert client.delete(f"{root}/attachments/{aid}", headers=auth).status_code == 202
    assert client.get(f"{root}/attachments/{aid}/download", headers=other).status_code == 410


def test_disabling_files_hides_message_file_metadata_and_blocks_attachment_claims(
    client, db_session, file_workspace, monkeypatch
):
    a, _, _, conversation = file_workspace
    auth = login(client, a.email)
    root = f"/api/v1/messaging/conversations/{conversation.id}"
    attachment = upload(client, auth, conversation.id).json()
    sent = client.post(
        f"{root}/messages",
        headers=auth,
        json={"body": "Attached notes", "attachment_ids": [attachment["id"]]},
    )
    assert sent.status_code == 201
    assert len(sent.json()["attachments"]) == 1

    monkeypatch.setattr(settings, "attachments_enabled", False)
    history = client.get(f"{root}/messages", headers=auth)
    assert history.status_code == 200
    assert history.json()["items"][0]["attachments"] == []

    blocked = client.post(
        f"{root}/messages",
        headers=auth,
        json={"body": "Try to attach again", "attachment_ids": [attachment["id"]]},
    )
    assert blocked.status_code == 503
    assert (
        db_session.scalar(select(Message).where(Message.body == "Try to attach again"))
        is None
    )


def test_membership_denials_and_validation(client, file_workspace, monkeypatch):
    a, _, outsider, c = file_workspace
    assert upload(client, login(client, outsider.email), c.id).status_code == 404
    assert upload(client, login(client, a.email), c.id, b"not pdf", "fake.pdf").status_code == 415
    assert upload(client, login(client, a.email), c.id, b"", "empty.txt").status_code == 415
    monkeypatch.setattr(settings, "attachment_max_bytes", 3)
    assert upload(client, login(client, a.email), c.id).status_code == 413


def test_claim_failure_rolls_back_message(client, db_session, file_workspace):
    a, b, _, c = file_workspace
    auth = login(client, a.email)
    aid = upload(client, auth, c.id).json()["id"]
    response = client.post(
        f"/api/v1/messaging/conversations/{c.id}/messages",
        headers=login(client, b.email),
        json={"body": "wrong owner", "attachment_ids": [aid]},
    )
    assert response.status_code == 404 or response.status_code == 409
    assert db_session.scalar(select(Message).where(Message.body == "wrong owner")) is None
    db_session.expire_all()
    assert db_session.get(Attachment, aid).status == "ready"


def test_scanner_failure_never_publishes(client, db_session, file_workspace, monkeypatch):
    a, _, _, c = file_workspace
    monkeypatch.setattr(settings, "allow_unscanned_development_files", False)
    response = upload(client, login(client, a.email), c.id)
    assert response.status_code == 503
    assert not list(db_session.scalars(select(Attachment).where(Attachment.status.in_(["ready", "attached"]))))


def test_equal_timestamp_conversation_pages_and_legacy_array(client, db_session, file_workspace):
    a, b, _, _ = file_workspace
    conversations = [create_group_conversation(
        db_session,
        a.organization_id,
        a.id,
        f"group {i}",
        [b.id],
    ) for i in range(102)]
    for c in conversations: c.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    auth = login(client, a.email)
    root = "/api/v1/messaging/conversations"
    seen, cursor = [], None
    while True:
        response = client.get(
            root + "/page",
            headers=auth,
            params={"limit": 50, **({"cursor": cursor} if cursor else {})},
        )
        assert response.status_code == 200, response.text
        page = response.json(); seen.extend(c["id"] for c in page["items"]); cursor = page["next_cursor"]
        if not cursor: break
    assert len(seen) == 103 and len(set(seen)) == 103
    legacy = client.get(root, headers=auth)
    assert isinstance(legacy.json(), list) and 'rel="next"' in legacy.headers["link"]
    assert client.get(root + "/page?cursor=garbage", headers=auth).status_code == 400


def test_upload_cleanup_delete_failure_preserves_retry_target(
    client, db_session, file_workspace, monkeypatch
):
    a, _, _, c = file_workspace
    underlying = LocalStorage(str(settings.storage_local_root))

    class UnreliableStorage:
        def create(self, key):
            return underlying.create(key)

        def open(self, key):
            return underlying.open(key)

        def delete(self, key):
            raise RuntimeError("Unexpected storage deletion failure")

    monkeypatch.setattr(
        attachment_service, "storage", lambda: UnreliableStorage()
    )

    response = upload(
        client,
        login(client, a.email),
        c.id,
        data=b"not a real PDF",
        filename="broken.pdf",
    )

    assert response.status_code == 415

    db_session.expire_all()
    item = db_session.scalar(
        select(Attachment).where(
            Attachment.organization_id == a.organization_id,
            Attachment.filename == "broken.pdf",
        )
    )

    assert item is not None
    assert item.status == "deleting"
    assert underlying.path(item.storage_key).exists()


def test_upload_abandon_failure_does_not_delete_storage_object(
    client, db_session, file_workspace, monkeypatch
):
    a, _, _, c = file_workspace
    underlying = LocalStorage(str(settings.storage_local_root))

    class UnreliableStorage:
        def create(self, key):
            return underlying.create(key)

        def open(self, key):
            return underlying.open(key)

        def delete(self, key):
            raise AssertionError("Storage deletion must not be attempted")

    monkeypatch.setattr(
        attachment_service, "storage", lambda: UnreliableStorage()
    )

    def fail_abandon(*args, **kwargs):
        raise RuntimeError("Database abandonment failed")

    monkeypatch.setattr(attachment_service, "abandon", fail_abandon)

    response = upload(
        client,
        login(client, a.email),
        c.id,
        data=b"not a real PDF",
        filename="abandon-failure.pdf",
    )

    assert response.status_code == 415

    db_session.expire_all()
    item = db_session.scalar(
        select(Attachment).where(
            Attachment.organization_id == a.organization_id,
            Attachment.filename == "abandon-failure.pdf",
        )
    )

    assert item is not None
    assert item.status == "uploading"
    assert underlying.path(item.storage_key).exists()


def test_upload_abort_failure_does_not_interrupt_abandonment(
    client, db_session, file_workspace, monkeypatch
):
    a, _, _, c = file_workspace
    underlying = LocalStorage(str(settings.storage_local_root))

    class BrokenWriter:
        def __init__(self, writer):
            self.writer = writer

        def write(self, data):
            raise RuntimeError("Original write failure")

        def abort(self):
            raise RuntimeError("Unexpected abort failure")

    class UnreliableStorage:
        def create(self, key):
            return BrokenWriter(underlying.create(key))

        def open(self, key):
            return underlying.open(key)

        def delete(self, key):
            underlying.delete(key)

    monkeypatch.setattr(
        attachment_service, "storage", lambda: UnreliableStorage()
    )

    response = upload(
        client,
        login(client, a.email),
        c.id,
        data=b"hello",
        filename="abort-failure.txt",
    )

    assert response.status_code == 503

    db_session.expire_all()
    item = db_session.scalar(
        select(Attachment).where(
            Attachment.organization_id == a.organization_id,
            Attachment.filename == "abort-failure.txt",
        )
    )

    assert item is not None
    assert item.status == "deleting"
