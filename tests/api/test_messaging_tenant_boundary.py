from app.core.security.password import hash_password
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.organization import Organization
from app.models.user import User


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


def test_other_organization_cannot_read_or_send_conversation_messages(
    client, db_session, organization
):
    other_org = Organization(
        name="Messaging Boundary Organization",
        slug="messaging-boundary-organization",
    )
    db_session.add(other_org)
    db_session.flush()

    owner = make_user(
        db_session, organization.id, "boundary.owner@example.com"
    )
    recipient = make_user(
        db_session, organization.id, "boundary.recipient@example.com"
    )
    outsider = make_user(
        db_session, other_org.id, "boundary.outsider@example.com"
    )

    conversation = Conversation(
        organization_id=organization.id,
        conversation_type="direct",
        created_by_user_id=owner.id,
        direct_user_low_id=min(owner.id, recipient.id),
        direct_user_high_id=max(owner.id, recipient.id),
        name=None,
    )
    db_session.add(conversation)
    db_session.flush()

    for user in (owner, recipient):
        db_session.add(
            ConversationMember(
                conversation_id=conversation.id,
                organization_id=organization.id,
                user_id=user.id,
                role="member",
                is_active=True,
            )
        )
    db_session.commit()

    headers = login(client, outsider.email)
    messages_url = (
        f"/api/v1/messaging/conversations/{conversation.id}/messages"
    )

    read_response = client.get(messages_url, headers=headers)
    assert read_response.status_code == 404
    assert read_response.json() == {"detail": "Conversation not found"}

    send_response = client.post(
        messages_url,
        headers=headers,
        json={"body": "Cross-organization access attempt"},
    )
    assert send_response.status_code == 404
    assert send_response.json() == {"detail": "Conversation not found"}
