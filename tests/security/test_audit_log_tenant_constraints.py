import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User


def _create_test_session():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine, Session(engine)


def _create_organizations_and_users(session):
    organization_a = Organization(
        name="Audit Organization A",
        slug="audit-organization-a",
    )
    organization_b = Organization(
        name="Audit Organization B",
        slug="audit-organization-b",
    )
    session.add_all([organization_a, organization_b])
    session.flush()

    tenant_user = User(
        organization_id=organization_a.id,
        email="audit-user-a@example.com",
        password_hash="test-hash",
        full_name="Audit User A",
        is_active=True,
    )
    other_tenant_user = User(
        organization_id=organization_b.id,
        email="audit-user-b@example.com",
        password_hash="test-hash",
        full_name="Audit User B",
        is_active=True,
    )
    super_admin = User(
        organization_id=None,
        email="audit-super-admin@example.com",
        password_hash="test-hash",
        full_name="Audit Super Admin",
        is_active=True,
        is_super_admin=True,
    )
    session.add_all([tenant_user, other_tenant_user, super_admin])
    session.commit()

    return organization_a, organization_b, tenant_user, other_tenant_user, super_admin


def _audit_log(organization_id, actor, actor_organization_id):
    return AuditLog(
        organization_id=organization_id,
        user_id=actor.id,
        actor_organization_id=actor_organization_id,
        action="USER_UPDATE",
        resource_type="user",
        resource_id=actor.id,
    )


def test_database_allows_tenant_actor_to_log_within_own_organization():
    engine, session = _create_test_session()
    try:
        org_a, _, tenant_user, _, _ = _create_organizations_and_users(session)

        session.add(_audit_log(org_a.id, tenant_user, org_a.id))
        session.commit()

        assert session.query(AuditLog).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_tenant_actor_logging_for_another_organization():
    engine, session = _create_test_session()
    try:
        org_a, org_b, _, tenant_user_b, _ = (
            _create_organizations_and_users(session)
        )

        session.add(_audit_log(org_a.id, tenant_user_b, org_b.id))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_allows_super_admin_to_log_for_customer_organization():
    engine, session = _create_test_session()
    try:
        org_a, _, _, _, super_admin = _create_organizations_and_users(session)

        session.add(_audit_log(org_a.id, super_admin, None))
        session.commit()

        saved = session.query(AuditLog).one()
        assert saved.organization_id == org_a.id
        assert saved.user_id == super_admin.id
        assert saved.actor_organization_id is None
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_tenant_actor_without_actor_organization():
    engine, session = _create_test_session()
    try:
        org_a, _, tenant_user, _, _ = _create_organizations_and_users(session)

        session.add(_audit_log(org_a.id, tenant_user, None))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_actor_organization_that_does_not_match_actor():
    engine, session = _create_test_session()
    try:
        org_a, org_b, tenant_user, _, _ = _create_organizations_and_users(session)

        session.add(_audit_log(org_a.id, tenant_user, org_b.id))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_updating_audit_log_to_another_organization():
    engine, session = _create_test_session()
    try:
        org_a, org_b, tenant_user, _, _ = (
            _create_organizations_and_users(session)
        )

        record = _audit_log(org_a.id, tenant_user, org_a.id)
        session.add(record)
        session.commit()

        record.organization_id = org_b.id

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    finally:
        session.close()
        engine.dispose()


def test_database_allows_super_admin_audit_log_update_for_customer():
    engine, session = _create_test_session()
    try:
        org_a, org_b, _, _, super_admin = (
            _create_organizations_and_users(session)
        )

        record = _audit_log(org_a.id, super_admin, None)
        session.add(record)
        session.commit()

        record.organization_id = org_b.id
        record.action = "BRANCH_UPDATE"
        session.commit()

        saved = session.query(AuditLog).one()
        assert saved.organization_id == org_b.id
        assert saved.user_id == super_admin.id
        assert saved.actor_organization_id is None
    finally:
        session.close()
        engine.dispose()


def test_database_rejects_super_admin_conversion_after_audit_record_exists():
    from sqlalchemy import update

    engine, session = _create_test_session()

    try:
        org_a, _, _, _, super_admin = (
            _create_organizations_and_users(session)
        )

        session.add(_audit_log(org_a.id, super_admin, None))
        session.commit()

        with pytest.raises(IntegrityError):
            session.execute(
                update(User)
                .where(User.id == super_admin.id)
                .values(
                    is_super_admin=False,
                    organization_id=org_a.id,
                )
            )
            session.commit()

        session.rollback()
    finally:
        session.close()
        engine.dispose()
