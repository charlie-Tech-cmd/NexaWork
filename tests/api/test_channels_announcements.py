from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


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


def grant_permissions(db, organization_id, user, names):
    role = Role(
        organization_id=organization_id,
        name=f"Test Admin {user.id}",
        is_active=True,
    )
    permissions = [
        Permission(name=name, description=name.replace("_", " ").title())
        for name in names
    ]
    db.add_all([role, *permissions])
    db.flush()
    db.execute(
        role_permissions.insert(),
        [
            {"role_id": role.id, "permission_id": permission.id}
            for permission in permissions
        ],
    )
    db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_channels_enforce_visibility_membership_and_moderation(
    client, db_session, organization
):
    creator = make_user(db_session, organization.id, "channel.admin@example.com")
    member = make_user(db_session, organization.id, "channel.member@example.com")
    outsider = make_user(
        db_session, organization.id, "channel.outsider@example.com"
    )
    other_org = Organization(
        name="Other Channel Organization",
        slug="other-channel-organization",
    )
    db_session.add(other_org)
    db_session.flush()
    cross_tenant = make_user(
        db_session, other_org.id, "channel.other@example.com"
    )
    grant_permissions(
        db_session,
        organization.id,
        creator,
        ["CHANNEL_CREATE"],
    )
    db_session.commit()

    creator_headers = login(client, creator.email)
    member_headers = login(client, member.email)
    outsider_headers = login(client, outsider.email)
    cross_tenant_headers = login(client, cross_tenant.email)

    denied_create = client.post(
        "/api/v1/channels",
        headers=member_headers,
        json={"name": "No permission", "visibility": "public"},
    )
    assert denied_create.status_code == 403

    public = client.post(
        "/api/v1/channels",
        headers=creator_headers,
        json={"name": "Engineering", "visibility": "public"},
    )
    assert public.status_code == 201, public.text
    public_id = public.json()["id"]
    assert public.json()["membership_role"] == "moderator"

    private = client.post(
        "/api/v1/channels",
        headers=creator_headers,
        json={"name": "People Operations", "visibility": "private"},
    )
    assert private.status_code == 201, private.text
    private_id = private.json()["id"]

    no_permission_list = client.get(
        "/api/v1/channels",
        headers=member_headers,
    )
    assert no_permission_list.status_code == 200
    assert [item["id"] for item in no_permission_list.json()["items"]] == [
        public_id
    ]

    denied_message = client.post(
        f"/api/v1/messaging/conversations/{public_id}/messages",
        headers=member_headers,
        json={"body": "Must join first"},
    )
    assert denied_message.status_code == 404

    denied_private_join = client.post(
        f"/api/v1/channels/{private_id}/join",
        headers=member_headers,
    )
    assert denied_private_join.status_code == 404

    joined = client.post(
        f"/api/v1/channels/{public_id}/join",
        headers=member_headers,
    )
    assert joined.status_code == 200, joined.text
    sent = client.post(
        f"/api/v1/messaging/conversations/{public_id}/messages",
        headers=member_headers,
        json={"body": "Shared channel update"},
    )
    assert sent.status_code == 201, sent.text

    invited = client.post(
        f"/api/v1/channels/{private_id}/members",
        headers=creator_headers,
        json={"user_id": member.id},
    )
    assert invited.status_code == 201, invited.text
    private_message = client.post(
        f"/api/v1/messaging/conversations/{private_id}/messages",
        headers=member_headers,
        json={"body": "Private collaboration"},
    )
    assert private_message.status_code == 201, private_message.text

    private_channels = client.get(
        "/api/v1/channels",
        headers=member_headers,
    ).json()["items"]
    assert {item["id"] for item in private_channels} == {public_id, private_id}

    outsider_read = client.get(
        f"/api/v1/messaging/conversations/{private_id}/messages",
        headers=outsider_headers,
    )
    assert outsider_read.status_code == 404
    cross_tenant_read = client.get(
        f"/api/v1/channels/{private_id}/members",
        headers=cross_tenant_headers,
    )
    assert cross_tenant_read.status_code == 404

    promoted = client.patch(
        f"/api/v1/channels/{private_id}/members/{member.id}",
        headers=creator_headers,
        json={"role": "moderator"},
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "moderator"

    demoted = client.patch(
        f"/api/v1/channels/{private_id}/members/{member.id}",
        headers=creator_headers,
        json={"role": "member"},
    )
    assert demoted.status_code == 200, demoted.text

    last_moderator = client.patch(
        f"/api/v1/channels/{private_id}/members/{creator.id}",
        headers=creator_headers,
        json={"role": "member"},
    )
    assert last_moderator.status_code == 400
    assert "at least one active moderator" in last_moderator.json()["detail"]


def test_announcements_are_organization_wide_and_admin_published(
    client, db_session, organization
):
    admin = make_user(db_session, organization.id, "announcement.admin@example.com")
    member = make_user(db_session, organization.id, "announcement.member@example.com")
    other_org = Organization(
        name="Other Announcement Organization",
        slug="other-announcement-organization",
    )
    db_session.add(other_org)
    db_session.flush()
    cross_tenant = make_user(
        db_session, other_org.id, "announcement.other@example.com"
    )
    grant_permissions(
        db_session,
        organization.id,
        admin,
        ["ANNOUNCEMENT_CREATE"],
    )
    db_session.commit()

    admin_headers = login(client, admin.email)
    member_headers = login(client, member.email)
    cross_tenant_headers = login(client, cross_tenant.email)

    denied = client.post(
        "/api/v1/announcements",
        headers=member_headers,
        json={"title": "Member post", "body": "Not permitted"},
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/v1/announcements",
        headers=admin_headers,
        json={"title": "  Office update  ", "body": "  New update  "},
    )
    assert created.status_code == 201, created.text
    assert created.json()["title"] == "Office update"
    assert created.json()["body"] == "New update"

    newer = client.post(
        "/api/v1/announcements",
        headers=admin_headers,
        json={"title": "Benefits note", "body": "Please review the update."},
    )
    assert newer.status_code == 201, newer.text

    member_feed = client.get(
        "/api/v1/announcements?limit=1",
        headers=member_headers,
    )
    assert member_feed.status_code == 200
    assert member_feed.json()["can_publish"] is False
    assert member_feed.json()["items"][0]["title"] == "Benefits note"
    assert member_feed.json()["next_cursor"] == newer.json()["id"]

    older_feed = client.get(
        f"/api/v1/announcements?limit=1&before_id={member_feed.json()['next_cursor']}",
        headers=member_headers,
    )
    assert older_feed.status_code == 200
    assert older_feed.json()["items"][0]["title"] == "Office update"
    assert older_feed.json()["next_cursor"] is None

    admin_feed = client.get(
        "/api/v1/announcements",
        headers=admin_headers,
    )
    assert admin_feed.json()["can_publish"] is True

    other_feed = client.get(
        "/api/v1/announcements",
        headers=cross_tenant_headers,
    )
    assert other_feed.status_code == 200
    assert other_feed.json()["items"] == []

    invalid = client.post(
        "/api/v1/announcements",
        headers=admin_headers,
        json={"title": "  ", "body": "Missing title"},
    )
    assert invalid.status_code == 422
