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
