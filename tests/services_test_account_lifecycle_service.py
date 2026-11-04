from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User
from app.services.account_lifecycle_service import (
    LifecycleTransitionError,
    decide_registration,
    mark_email_verified,
)
from app.services.user_service import update_user


def create_lifecycle_user(db_session, organization, email, **overrides):
    user = User(
        organization_id=organization.id,
        email=email,
        password_hash="test-password-hash",
        full_name="Lifecycle User",
        lifecycle_managed=True,
        approval_status="pending",
        is_active=False,
        **overrides,
    )
    db_session.add(user)
    db_session.flush()
    return user


def create_organization(db_session, slug):
    organization = Organization(
        name=slug,
        slug=slug,
    )
    db_session.add(organization)
    db_session.flush()
    return organization


def test_legacy_user_is_not_marked_verified_or_lifecycle_managed(db_session):
    organization = create_organization(db_session, "legacy-user-org")
    user = User(
        organization_id=organization.id,
        email="legacy@example.com",
        password_hash="test-password-hash",
        full_name="Legacy User",
    )
    db_session.add(user)
    db_session.flush()

    assert user.lifecycle_managed is False
    assert user.approval_status == "approved"
    assert user.email_verified_at is None
    assert user.is_active is True


def test_mark_email_verified_records_time_and_audit_event(db_session):
    organization = create_organization(db_session, "verification-org")
    user = create_lifecycle_user(
        db_session,
        organization,
        "verify@example.com",
    )

    verified_user = mark_email_verified(
        db_session,
        user_id=user.id,
        organization_id=organization.id,
    )

    assert verified_user.email_verified_at is not None
    assert verified_user.approval_status == "pending"
    assert verified_user.is_active is False

    audit_log = db_session.query(AuditLog).one()
    assert audit_log.action == "USER_EMAIL_VERIFIED"
    assert audit_log.user_id == user.id
    assert audit_log.resource_id == user.id


def test_email_verification_is_single_use(db_session):
    organization = create_organization(db_session, "single-use-org")
    user = create_lifecycle_user(
        db_session,
        organization,
        "single-use@example.com",
    )
    mark_email_verified(
        db_session,
        user_id=user.id,
        organization_id=organization.id,
    )

    with pytest.raises(ValueError, match="already verified"):
        mark_email_verified(
            db_session,
            user_id=user.id,
            organization_id=organization.id,
        )


def test_approval_requires_verified_email_and_cannot_be_self_approved(
    db_session,
):
    organization = create_organization(db_session, "approval-org")
    actor = User(
        organization_id=organization.id,
        email="approver@example.com",
        password_hash="test-password-hash",
        full_name="Approver",
    )
    user = create_lifecycle_user(
        db_session,
        organization,
        "pending@example.com",
    )
    db_session.add(actor)
    db_session.flush()

    with pytest.raises(ValueError, match="Email verification is required"):
        decide_registration(
            db_session,
            user_id=user.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            decision="approved",
        )

    user.email_verified_at = datetime.now(timezone.utc)
    db_session.flush()

    with pytest.raises(ValueError, match="cannot approve their own"):
        decide_registration(
            db_session,
            user_id=user.id,
            organization_id=organization.id,
            actor_user_id=user.id,
            decision="approved",
        )


def test_approval_activates_verified_user_and_records_actor(db_session):
    organization = create_organization(db_session, "approved-org")
    actor = User(
        organization_id=organization.id,
        email="admin@example.com",
        password_hash="test-password-hash",
        full_name="Organization Admin",
    )
    user = create_lifecycle_user(
        db_session,
        organization,
        "approved@example.com",
        email_verified_at=datetime.now(timezone.utc),
    )
    db_session.add(actor)
    db_session.flush()
    original_token_version = user.token_version

    approved_user = decide_registration(
        db_session,
        user_id=user.id,
        organization_id=organization.id,
        actor_user_id=actor.id,
        decision="approved",
    )

    assert approved_user.approval_status == "approved"
    assert approved_user.is_active is True
    assert approved_user.token_version == original_token_version + 1
    audit_log = db_session.query(AuditLog).filter_by(
        resource_id=user.id,
    ).one()
    assert audit_log.user_id == actor.id
    assert audit_log.action == "EMPLOYEE_REGISTRATION_APPROVED"


def test_rejection_is_terminal_and_cannot_authenticate(db_session):
    organization = create_organization(db_session, "rejected-org")
    actor = User(
        organization_id=organization.id,
        email="rejector@example.com",
        password_hash="test-password-hash",
        full_name="Organization Admin",
    )
    user = create_lifecycle_user(
        db_session,
        organization,
        "rejected@example.com",
        email_verified_at=datetime.now(timezone.utc),
    )
    db_session.add(actor)
    db_session.flush()

    rejected_user = decide_registration(
        db_session,
        user_id=user.id,
        organization_id=organization.id,
        actor_user_id=actor.id,
        decision="rejected",
    )

    assert rejected_user.approval_status == "rejected"
    assert rejected_user.is_active is False

    with pytest.raises(ValueError, match="not pending"):
        decide_registration(
            db_session,
            user_id=user.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            decision="approved",
        )


def test_managed_pending_user_cannot_be_activated_by_user_update(
    db_session,
):
    organization = create_organization(db_session, "activation-org")
    actor = User(
        organization_id=organization.id,
        email="activation-admin@example.com",
        password_hash="test-password-hash",
        full_name="Organization Admin",
    )
    user = create_lifecycle_user(
        db_session,
        organization,
        "activation-pending@example.com",
    )
    db_session.add(actor)
    db_session.commit()

    with pytest.raises(
        LifecycleTransitionError,
        match="Email verification and approval",
    ):
        update_user(
            db=db_session,
            user_id=user.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            email=None,
            full_name=None,
            is_active=True,
        )

    db_session.rollback()
    assert user.is_active is False


def test_approval_actor_must_belong_to_the_registration_organization(
    db_session,
):
    organization = create_organization(db_session, "target-organization")
    other_organization = create_organization(
        db_session,
        "other-organization",
    )
    actor = User(
        organization_id=other_organization.id,
        email="cross-tenant-admin@example.com",
        password_hash="test-password-hash",
        full_name="Other Organization Admin",
    )
    user = create_lifecycle_user(
        db_session,
        organization,
        "cross-tenant-target@example.com",
        email_verified_at=datetime.now(timezone.utc),
    )
    db_session.add(actor)
    db_session.flush()

    with pytest.raises(ValueError, match="Approver not found in organization"):
        decide_registration(
            db_session,
            user_id=user.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            decision="approved",
        )

    assert user.approval_status == "pending"
    assert user.is_active is False


def test_database_rejects_active_lifecycle_user_without_verification(
    db_session,
):
    organization = create_organization(db_session, "constraint-org")
    user = User(
        organization_id=organization.id,
        email="unverified-active@example.com",
        password_hash="test-password-hash",
        full_name="Unverified User",
        lifecycle_managed=True,
        approval_status="approved",
        is_active=True,
    )
    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_changing_managed_user_email_requires_reverification(db_session):
    organization = create_organization(db_session, "email-change-org")
    actor = User(
        organization_id=organization.id,
        email="email-change-admin@example.com",
        password_hash="test-password-hash",
        full_name="Organization Admin",
    )
    user = User(
        organization_id=organization.id,
        email="verified@example.com",
        password_hash="test-password-hash",
        full_name="Verified User",
        lifecycle_managed=True,
        email_verified_at=datetime.now(timezone.utc),
        approval_status="approved",
        is_active=True,
    )
    db_session.add_all([actor, user])
    db_session.commit()
    original_token_version = user.token_version

    updated_user = update_user(
        db=db_session,
        user_id=user.id,
        organization_id=organization.id,
        actor_user_id=actor.id,
        email="changed@example.com",
        full_name=None,
        is_active=None,
    )

    assert updated_user.email == "changed@example.com"
    assert updated_user.email_verified_at is None
    assert updated_user.is_active is False
    assert updated_user.token_version == original_token_version + 1
