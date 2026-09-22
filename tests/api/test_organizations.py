from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.user import User


def test_get_organization_rejects_another_organization(
    client,
    db_session,
):
    organization_a = Organization(
        name="Organization A",
        slug="organization-api-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="organization-api-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="organization.api.a@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "organization.api.a@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/organizations/{organization_b.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Organization not found",
    }


def test_get_organization_allows_current_organization(
    client,
    db_session,
):
    organization = Organization(
        name="Current Organization",
        slug="current-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="current.organization@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Current Organization User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "current.organization@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        f"/organizations/{organization.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == organization.id
    assert response_data["name"] == "Current Organization"
    assert response_data["slug"] == "current-organization"
    assert response_data["is_active"] is True
    assert response_data["created_at"] is not None
    assert response_data["updated_at"] is not None