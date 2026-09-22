from app.api.dependencies import require_permission
from app.core.security.password import hash_password
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def create_rbac_test_data(db_session):
    organization = Organization(
        name="RBAC Test Organization",
        slug="rbac-test-organization",
    )
    db_session.add(organization)
    db_session.flush()

    permission = Permission(
        name="USER_VIEW",
        description="View users",
    )
    db_session.add(permission)
    db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="User Viewer",
        description="Can view users",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="rbac.test@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="RBAC Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user.id,
            role_id=role.id,
        )
    )

    db_session.commit()

    return organization, permission, role, user


def test_require_permission_allows_user_with_permission(db_session):
    _, _, _, user = create_rbac_test_data(db_session)

    dependency = require_permission("USER_VIEW")

    result = dependency(
        current_user=user,
        db=db_session,
    )

    assert result.id == user.id


def test_require_permission_rejects_user_without_permission(db_session):
    organization = Organization(
        name="No Permission Organization",
        slug="no-permission-organization",
    )
    db_session.add(organization)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        email="no.permission@example.com",
        password_hash="test-hash",
        full_name="No Permission User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    dependency = require_permission("USER_VIEW")

    try:
        dependency(
            current_user=user,
            db=db_session,
        )
    except Exception as exc:
        assert exc.status_code == 403
        assert exc.detail == "Permission denied"
    else:
        raise AssertionError("Expected permission to be rejected")


def test_require_permission_rejects_role_from_another_organization(db_session):
    organization_a = Organization(
        name="Organization A",
        slug="organization-a",
    )
    organization_b = Organization(
        name="Organization B",
        slug="organization-b",
    )
    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    permission = Permission(
        name="USER_VIEW",
        description="View users",
    )
    db_session.add(permission)
    db_session.flush()

    role_b = Role(
        organization_id=organization_b.id,
        name="Organization B Viewer",
        is_active=True,
    )
    db_session.add(role_b)
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="org-a.user@example.com",
        password_hash="test-hash",
        full_name="Organization A User",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role_b.id,
            permission_id=permission.id,
        )
    )

    db_session.execute(
        user_roles.insert().values(
            user_id=user_a.id,
            role_id=role_b.id,
        )
    )

    db_session.commit()

    dependency = require_permission("USER_VIEW")

    try:
        dependency(
            current_user=user_a,
            db=db_session,
        )
    except Exception as exc:
        assert exc.status_code == 403
        assert exc.detail == "Permission denied"
    else:
        raise AssertionError(
            "Expected cross-organization role to be rejected"
        )


def test_require_permission_rejects_inactive_role(db_session):
    _, _, role, user = create_rbac_test_data(db_session)

    role.is_active = False
    db_session.commit()

    dependency = require_permission("USER_VIEW")

    try:
        dependency(
            current_user=user,
            db=db_session,
        )
    except Exception as exc:
        assert exc.status_code == 403
        assert exc.detail == "Permission denied"
    else:
        raise AssertionError("Expected inactive role to be rejected")
