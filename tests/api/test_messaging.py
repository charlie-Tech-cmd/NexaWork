from app.core.security.password import hash_password
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.organization import Organization
from app.models.user import User
from app.services.messaging_service import create_or_get_direct_conversation


PASSWORD = "SecurePassword123!"


def make_user(db, organization_id, email):
    user = User(
        organization_id=organization_id,
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name=email.split("@")[0],
        is_active=True,
        is_super_admin=False,
    )
    db.add(user)
    db.flush()
    return user


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_messaging_requires_authentication(client):
    response = client.get("/api/v1/messaging/conversations")
    assert response.status_code == 401


def test_direct_conversation_can_be_created_and_reused(
    client, db_session, organization
):
    creator = make_user(
        db_session, organization.id, "messaging.creator@example.com"
    )
    recipient = make_user(
        db_session, organization.id, "messaging.recipient@example.com"
    )
    db_session.commit()
    headers = login(client, creator.email)

    first = client.post(
        "/api/v1/messaging/direct",
        headers=headers,
        json={"recipient_user_id": recipient.id},
    )
    assert first.status_code == 200, first.text
    assert first.json()["conversation_type"] == "direct"

    second = client.post(
        "/api/v1/messaging/direct",
        headers=headers,
        json={"recipient_user_id": recipient.id},
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]


def test_direct_conversation_rejects_other_organization_user(
    client, db_session, organization
):
    other_org = Organization(
        name="Messaging Other Organization",
        slug="messaging-other-organization",
    )
    db_session.add(other_org)
    db_session.flush()

    creator = make_user(
        db_session, organization.id, "messaging.tenant.a@example.com"
    )
    outsider = make_user(
        db_session, other_org.id, "messaging.tenant.b@example.com"
    )
    db_session.commit()

    response = client.post(
        "/api/v1/messaging/direct",
        headers=login(client, creator.email),
        json={"recipient_user_id": outsider.id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "User is unavailable in this organization"
    )



def test_group_creation_and_member_message_flow(
    client, db_session, organization
):
    creator = make_user(
        db_session, organization.id, "messaging.group.creator@example.com"
    )
    member = make_user(
        db_session, organization.id, "messaging.group.member@example.com"
    )
    outsider = make_user(
        db_session, organization.id, "messaging.group.outsider@example.com"
    )
    db_session.commit()

    creator_headers = login(client, creator.email)
    member_headers = login(client, member.email)
    outsider_headers = login(client, outsider.email)

    group_response = client.post(
        "/api/v1/messaging/groups",
        headers=creator_headers,
        json={
            "name": "Engineering",
            "member_user_ids": [member.id],
        },
    )
    assert group_response.status_code == 201, group_response.text
    conversation_id = group_response.json()["id"]

    sent = client.post(
        f"/api/v1/messaging/conversations/{conversation_id}/messages",
        headers=member_headers,
        json={"body": "  Hello team  "},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["body"] == "Hello team"

    received = client.get(
        f"/api/v1/messaging/conversations/{conversation_id}/messages",
        headers=creator_headers,
    )
    assert received.status_code == 200, received.text
    assert [item["body"] for item in received.json()["items"]] == [
        "Hello team"
    ]

    denied_read = client.get(
        f"/api/v1/messaging/conversations/{conversation_id}/messages",
        headers=outsider_headers,
    )
    assert denied_read.status_code == 404
    assert denied_read.json() == {"detail": "Conversation not found"}

    denied_send = client.post(
        f"/api/v1/messaging/conversations/{conversation_id}/messages",
        headers=outsider_headers,
        json={"body": "I should not see this"},
    )
    assert denied_send.status_code == 404
    assert denied_send.json() == {"detail": "Conversation not found"}


def test_conversation_list_only_returns_active_memberships(
    client, db_session, organization
):
    user = make_user(
        db_session, organization.id, "messaging.list.user@example.com"
    )
    other = make_user(
        db_session, organization.id, "messaging.list.other@example.com"
    )
    db_session.commit()

    visible = create_or_get_direct_conversation(
        db_session, organization.id, user.id, other.id
    )

    hidden = Conversation(
        organization_id=organization.id,
        conversation_type="group",
        name="Inactive membership group",
        created_by_user_id=other.id,
    )
    db_session.add(hidden)
    db_session.flush()
    db_session.add(
        ConversationMember(
            conversation_id=hidden.id,
            organization_id=organization.id,
            user_id=user.id,
            role="member",
            is_active=False,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/messaging/conversations",
        headers=login(client, user.email),
    )

    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()}
    assert visible.id in ids
    assert hidden.id not in ids


def test_message_validation_and_pagination_parameters(
    client, db_session, organization
):
    user = make_user(
        db_session, organization.id, "messaging.validation@example.com"
    )
    other = make_user(
        db_session, organization.id, "messaging.validation.other@example.com"
    )
    db_session.commit()

    conversation = create_or_get_direct_conversation(
        db_session, organization.id, user.id, other.id
    )
    headers = login(client, user.email)
    base = (
        f"/api/v1/messaging/conversations/{conversation.id}/messages"
    )

    blank = client.post(
        base, headers=headers, json={"body": "   "}
    )
    assert blank.status_code == 422

    invalid_limit = client.get(
        f"{base}?limit=0", headers=headers
    )
    assert invalid_limit.status_code == 422

    invalid_cursor = client.get(
        f"{base}?before_id=0", headers=headers
    )
    assert invalid_cursor.status_code == 422


def test_messaging_api_enforces_pagination_and_cursor_boundaries(
    client, db_session, organization
):
    user = make_user(
        db_session, organization.id, "messaging.pagination@example.com"
    )
    recipients = [
        make_user(
            db_session,
            organization.id,
            f"messaging.pagination.{index}@example.com",
        )
        for index in range(3)
    ]
    db_session.commit()

    headers = login(client, user.email)

    conversations = [
        create_or_get_direct_conversation(
            db_session, organization.id, user.id, recipient.id
        )
        for recipient in recipients
    ]

    conversation_response = client.get(
        "/api/v1/messaging/conversations?limit=1",
        headers=headers,
    )
    assert conversation_response.status_code == 200
    assert len(conversation_response.json()) == 1

    for invalid_limit in (0, 101):
        response = client.get(
            f"/api/v1/messaging/conversations?limit={invalid_limit}",
            headers=headers,
        )
        assert response.status_code == 422

    conversation_id = conversations[0].id
    created_messages = [
        client.post(
            f"/api/v1/messaging/conversations/{conversation_id}/messages",
            headers=headers,
            json={"body": body},
        )
        for body in ("one", "two", "three", "four")
    ]
    assert all(response.status_code == 201 for response in created_messages)

    first_page_response = client.get(
        f"/api/v1/messaging/conversations/{conversation_id}/messages?limit=2",
        headers=headers,
    )
    assert first_page_response.status_code == 200
    first_page = first_page_response.json()

    assert [item["body"] for item in first_page["items"]] == ["three", "four"]
    assert first_page["next_cursor"] == created_messages[2].json()["id"]

    older_page_response = client.get(
        (
            f"/api/v1/messaging/conversations/{conversation_id}/messages"
            f"?limit=2&before_id={first_page['next_cursor']}"
        ),
        headers=headers,
    )
    assert older_page_response.status_code == 200
    older_page = older_page_response.json()

    assert [item["body"] for item in older_page["items"]] == ["one", "two"]
    assert older_page["next_cursor"] is None

    for invalid_limit in (0, 101):
        response = client.get(
            (
                f"/api/v1/messaging/conversations/{conversation_id}/messages"
                f"?limit={invalid_limit}"
            ),
            headers=headers,
        )
        assert response.status_code == 422
