from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security.password import hash_password
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.organization import Organization
from app.models.user import User
from app.services.messaging_service import (
    ConversationAccessError,
    _is_direct_pair_unique_violation,
    create_group_conversation,
    create_or_get_direct_conversation,
    list_conversations,
    list_messages,
    send_message,
)


def test_direct_pair_unique_violation_recognizes_sqlite_constraint():
    exc = IntegrityError(
        "statement",
        {},
        Exception(
            "UNIQUE constraint failed: conversations.organization_id, "
            "conversations.direct_user_low_id, conversations.direct_user_high_id"
        ),
    )
    assert _is_direct_pair_unique_violation(exc)


def test_unrelated_integrity_error_is_not_a_direct_pair_conflict():
    exc = IntegrityError(
        "statement", {}, Exception("UNIQUE constraint failed: users.email")
    )
    assert not _is_direct_pair_unique_violation(exc)


def make_user(db, organization_id, email, *, active=True):
    user = User(
        organization_id=organization_id,
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        full_name=email.split("@")[0],
        is_active=active,
        is_super_admin=False,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def messaging_users(db_session, organization):
    other_org = Organization(
        name="Other Organization",
        slug="other-messaging-organization",
    )
    db_session.add(other_org)
    db_session.flush()

    creator = make_user(
        db_session, organization.id, "creator@example.com"
    )
    recipient = make_user(
        db_session, organization.id, "recipient@example.com"
    )
    third = make_user(
        db_session, organization.id, "third@example.com"
    )
    outsider = make_user(
        db_session, other_org.id, "outsider@example.com"
    )
    inactive = make_user(
        db_session, organization.id, "inactive@example.com", active=False
    )

    return {
        "organization_id": organization.id,
        "creator": creator,
        "recipient": recipient,
        "third": third,
        "outsider": outsider,
        "inactive": inactive,
    }


def test_direct_conversation_is_created_and_reused(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]

    first = create_or_get_direct_conversation(
        db_session, org_id, data["creator"].id, data["recipient"].id
    )
    second = create_or_get_direct_conversation(
        db_session, org_id, data["recipient"].id, data["creator"].id
    )

    assert first.id == second.id
    assert first.conversation_type == "direct"

    members = db_session.scalars(
        select(ConversationMember).where(
            ConversationMember.conversation_id == first.id
        )
    ).all()
    assert {member.user_id for member in members} == {
        data["creator"].id,
        data["recipient"].id,
    }


def test_direct_conversation_reuse_rejects_inactive_membership(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]

    conversation = create_or_get_direct_conversation(
        db_session, org_id, data["creator"].id, data["recipient"].id
    )

    membership = db_session.scalar(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation.id,
            ConversationMember.user_id == data["recipient"].id,
        )
    )
    membership.is_active = False
    db_session.commit()

    with pytest.raises(ConversationAccessError):
        create_or_get_direct_conversation(
            db_session, org_id, data["creator"].id, data["recipient"].id
        )

    db_session.refresh(membership)
    assert membership.is_active is False


def test_direct_conversation_rejects_self_and_cross_org(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]

    with pytest.raises(ValueError):
        create_or_get_direct_conversation(
            db_session, org_id, data["creator"].id, data["creator"].id
        )

    with pytest.raises(ValueError):
        create_or_get_direct_conversation(
            db_session, org_id, data["creator"].id, data["outsider"].id
        )


def test_direct_conversation_rejects_inactive_recipient(
    db_session, messaging_users
):
    data = messaging_users
    with pytest.raises(ValueError):
        create_or_get_direct_conversation(
            db_session,
            data["organization_id"],
            data["creator"].id,
            data["inactive"].id,
        )


def test_group_creator_is_admin_and_members_are_scoped(
    db_session, messaging_users
):
    data = messaging_users
    group = create_group_conversation(
        db_session,
        data["organization_id"],
        data["creator"].id,
        "  Engineering  ",
        [data["recipient"].id, data["third"].id],
    )

    assert group.name == "Engineering"
    members = db_session.scalars(
        select(ConversationMember).where(
            ConversationMember.conversation_id == group.id
        )
    ).all()
    roles = {member.user_id: member.role for member in members}
    assert roles[data["creator"].id] == "admin"
    assert roles[data["recipient"].id] == "member"
    assert roles[data["third"].id] == "member"


def test_group_rejects_cross_org_or_inactive_member(
    db_session, messaging_users
):
    data = messaging_users

    for member_id in (data["outsider"].id, data["inactive"].id):
        with pytest.raises(ValueError):
            create_group_conversation(
                db_session,
                data["organization_id"],
                data["creator"].id,
                "Invalid group",
                [member_id],
            )


def test_group_rejects_duplicate_ids_and_too_many_members(
    db_session, messaging_users
):
    data = messaging_users

    with pytest.raises(ValueError):
        create_group_conversation(
            db_session,
            data["organization_id"],
            data["creator"].id,
            "Duplicate",
            [data["recipient"].id, data["recipient"].id],
        )

    with pytest.raises(ValueError):
        create_group_conversation(
            db_session,
            data["organization_id"],
            data["creator"].id,
            "Too large",
            list(range(10000, 10100)),
        )


def test_only_active_members_can_send_or_read_messages(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]
    conversation = create_or_get_direct_conversation(
        db_session, org_id, data["creator"].id, data["recipient"].id
    )

    message = send_message(
        db_session,
        org_id,
        conversation.id,
        data["creator"].id,
        "  Hello  ",
    )
    assert message.body == "Hello"

    with pytest.raises(ValueError):
        send_message(
            db_session, org_id, conversation.id, data["third"].id, "Intruder"
        )

    outsider_conversation = Conversation(
        organization_id=org_id,
        conversation_type="group",
        name="Private",
        created_by_user_id=data["creator"].id,
    )
    db_session.add(outsider_conversation)
    db_session.flush()
    db_session.add(
        ConversationMember(
            conversation_id=outsider_conversation.id,
            organization_id=org_id,
            user_id=data["third"].id,
            role="member",
            is_active=False,
        )
    )
    db_session.commit()

    with pytest.raises(ValueError):
        list_messages(
            db_session, org_id, outsider_conversation.id, data["third"].id
        )


def test_message_pagination_is_chronological(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]
    conversation = create_or_get_direct_conversation(
        db_session, org_id, data["creator"].id, data["recipient"].id
    )

    created = [
        send_message(
            db_session, org_id, conversation.id, data["creator"].id, body
        )
        for body in ("one", "two", "three", "four")
    ]

    page, cursor = list_messages(
        db_session,
        org_id,
        conversation.id,
        data["recipient"].id,
        limit=2,
    )
    assert [item.body for item in page] == ["three", "four"]
    assert cursor == created[2].id

    older_page, older_cursor = list_messages(
        db_session,
        org_id,
        conversation.id,
        data["recipient"].id,
        before_id=cursor,
        limit=2,
    )
    assert [item.body for item in older_page] == ["one", "two"]
    assert older_cursor is None


def test_conversation_listing_only_returns_active_memberships(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]
    conversation = create_or_get_direct_conversation(
        db_session, org_id, data["creator"].id, data["recipient"].id
    )

    visible = list_conversations(db_session, org_id, data["creator"].id)
    assert conversation.id in {item.id for item in visible}

    membership = db_session.scalar(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation.id,
            ConversationMember.user_id == data["creator"].id,
        )
    )
    membership.is_active = False
    db_session.commit()

    visible = list_conversations(db_session, org_id, data["creator"].id)
    assert conversation.id not in {item.id for item in visible}


def test_conversation_listing_orders_by_created_at_descending(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]
    creator_id = data["creator"].id

    older = create_or_get_direct_conversation(
        db_session, org_id, creator_id, data["recipient"].id
    )
    newer = create_or_get_direct_conversation(
        db_session, org_id, creator_id, data["third"].id
    )

    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    db_session.commit()

    ordered = list_conversations(db_session, org_id, creator_id)

    assert [item.id for item in ordered] == [newer.id, older.id]


def test_conversation_listing_uses_id_tiebreaker_and_respects_limit(
    db_session, messaging_users
):
    data = messaging_users
    org_id = data["organization_id"]
    creator_id = data["creator"].id

    conversations = [
        create_or_get_direct_conversation(
            db_session, org_id, creator_id, recipient.id
        )
        for recipient in (data["recipient"], data["third"])
    ]

    shared_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    conversations[0].created_at = shared_time
    conversations[1].created_at = shared_time
    db_session.commit()

    # The higher ID must appear first when timestamps are equal.
    ordered = list_conversations(db_session, org_id, creator_id)
    assert [item.id for item in ordered] == [
        conversations[1].id,
        conversations[0].id,
    ]

    limited = list_conversations(db_session, org_id, creator_id, limit=1)
    assert [item.id for item in limited] == [conversations[1].id]
