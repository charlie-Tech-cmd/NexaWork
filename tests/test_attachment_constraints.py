import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.base import Base
from app.models.organization import Organization
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.attachment import Attachment


@pytest.mark.parametrize(
    "violation",
    ["conversation_tenant", "uploader_tenant", "message_conversation", "empty_ready"],
)
def test_attachment_constraints_reject_invalid_scope_and_lifecycle(violation):
    engine = create_engine("sqlite:///:memory:")
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _): connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            a, b = Organization(name="A", slug="constraint-a"), Organization(name="B", slug="constraint-b")
            db.add_all([a,b]); db.flush()
            ua = User(organization_id=a.id, email="ca@example.com", full_name="A", password_hash="test-only")
            ub = User(organization_id=b.id, email="cb@example.com", full_name="B", password_hash="test-only")
            db.add_all([ua,ub]);db.flush()
            ca = Conversation(organization_id=a.id, created_by_user_id=ua.id, conversation_type="group", name="A")
            ca2 = Conversation(
                organization_id=a.id,
                created_by_user_id=ua.id,
                conversation_type="group",
                name="A2",
            )
            cb = Conversation(organization_id=b.id, created_by_user_id=ub.id, conversation_type="group", name="B")
            db.add_all([ca,ca2,cb]);db.flush()
            message = Message(organization_id=a.id, conversation_id=ca2.id, sender_id=ua.id, body="caption")
            db.add(message);db.flush()
            from datetime import datetime, timezone
            item = Attachment(organization_id=a.id, conversation_id=ca.id, uploaded_by_user_id=ua.id, storage_key="a"*32,
                filename="a.txt", content_type="text/plain", size_bytes=1, sha256="b"*64, status="ready", expires_at=datetime.now(timezone.utc))
            if violation == "conversation_tenant": item.conversation_id=cb.id
            if violation == "uploader_tenant": item.uploaded_by_user_id=ub.id
            if violation == "message_conversation": item.message_id=message.id; item.status="attached"
            if violation == "empty_ready": item.size_bytes=0
            db.add(item)
            with pytest.raises(IntegrityError): db.flush()
    finally:
        engine.dispose()
