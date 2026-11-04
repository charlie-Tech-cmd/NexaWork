from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security.password import hash_password
from app.core.rate_limit import RateLimitUnavailable
from app.services.email.service import EmailDeliveryUnavailable
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.department import Department
from app.models.email_verification_token import EmailVerificationToken
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.organization_registration_code import (
    OrganizationRegistrationCode,
)
from app.models.permission import Permission
from app.models.region import Region
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles


def create_registration_workspace(db_session, slug):
    organization = Organization(
        name=f"Organization {slug}",
        slug=slug,
    )
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name=f"Region {slug}",
        slug=f"region-{slug}",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name=f"Branch {slug}",
        slug=f"branch-{slug}",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name=f"Department {slug}",
        slug=f"department-{slug}",
    )
    db_session.add(department)
    db_session.flush()
    return organization, branch, department


def create_org_admin(db_session, organization, email):
    permission = db_session.scalar(
        select(Permission).where(Permission.name == "ADMIN_ACCESS")
    )
    if permission is None:
        permission = Permission(
            name="ADMIN_ACCESS",
            description="Administrative access",
            is_active=True,
        )
        db_session.add(permission)
        db_session.flush()

    role = Role(
        organization_id=organization.id,
        name=f"Admin {organization.slug}",
        description="Organization administrator",
        is_active=True,
    )
    admin = User(
        organization_id=organization.id,
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Administrator",
        is_active=True,
    )
    db_session.add_all([role, admin])
    db_session.flush()
    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=permission.id,
        )
    )
    db_session.execute(
        user_roles.insert().values(
            user_id=admin.id,
            role_id=role.id,
        )
    )
    db_session.commit()
    return admin


def registration_payload(code, branch_id, department_id, **overrides):
    return {
        "organization_code": code,
        "email": "new.employee@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "full_name": "New Employee",
        "employee_id": "EMP-REG-001",
        "branch_id": branch_id,
        "department_id": department_id,
        "job_title": "Engineer",
        **overrides,
    }


def create_pending_employee_registration(
    db_session,
    organization,
    branch,
    department,
    *,
    email,
    employee_id,
    verified,
):
    user = User(
        organization_id=organization.id,
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        full_name="Pending Registration",
        is_active=False,
        lifecycle_managed=True,
        approval_status="pending",
        email_verified_at=(
            datetime.now(timezone.utc) if verified else None
        ),
    )
    db_session.add(user)
    db_session.flush()
    employee = Employee(
        organization_id=organization.id,
        user_id=user.id,
        employee_id=employee_id,
        branch_id=branch.id,
        department_id=department.id,
        job_title="Engineer",
        is_active=False,
    )
    db_session.add(employee)
    db_session.commit()
    return user, employee


def verification_token_from_email(email):
    verification_link = next(
        line for line in email["body"].splitlines() if "token=" in line
    )
    return parse_qs(urlsplit(verification_link).query)["token"][0]


def allow_registration_rate_limits(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.is_registration_ip_allowed",
        lambda key: True,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.is_registration_code_allowed",
        lambda key: True,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.is_registration_identity_allowed",
        lambda key: True,
    )


def create_admin_registration_code(client, db_session, admin):
    login_response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": admin.email,
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200
    headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}",
    }
    response = client.post(
        "/api/v1/organizations/me/registration-code",
        json={"expires_in_days": 30},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["code"], headers


def test_admin_can_rotate_and_revoke_registration_code(
    client,
    db_session,
):
    organization, _, _ = create_registration_workspace(
        db_session,
        "registration-code-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration.admin@example.com",
    )
    first_code, headers = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    first_record = db_session.scalar(
        select(OrganizationRegistrationCode)
    )
    assert first_record is not None
    assert first_record.code_hash != first_code
    assert len(first_record.code_hash) == 64

    second_response = client.post(
        "/api/v1/organizations/me/registration-code",
        json={"expires_in_days": None},
        headers=headers,
    )
    assert second_response.status_code == 201
    second_code = second_response.json()["code"]

    first_validation = client.post(
        "/api/v1/auth/registration-code/validate",
        json={"code": first_code},
    )
    second_validation = client.post(
        "/api/v1/auth/registration-code/validate",
        json={"code": second_code},
    )
    assert first_validation.json() == {"valid": False}
    assert second_validation.json() == {"valid": True}

    revoke_response = client.delete(
        "/api/v1/organizations/me/registration-code",
        headers=headers,
    )
    assert revoke_response.status_code == 204
    assert client.post(
        "/api/v1/auth/registration-code/validate",
        json={"code": second_code},
    ).json() == {"valid": False}

    actions = db_session.scalars(
        select(AuditLog.action).where(
            AuditLog.resource_type == "organization_registration_code",
            AuditLog.organization_id == organization.id,
        )
    ).all()
    assert actions == [
        "ORGANIZATION_REGISTRATION_CODE_CREATE",
        "ORGANIZATION_REGISTRATION_CODE_CREATE",
        "ORGANIZATION_REGISTRATION_CODE_REVOKE",
    ]


def test_non_admin_cannot_create_registration_code(client, db_session):
    organization, _, _ = create_registration_workspace(
        db_session,
        "registration-code-forbidden",
    )
    user = User(
        organization_id=organization.id,
        email="registration.member@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Member",
    )
    db_session.add(user)
    db_session.commit()
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )

    response = client.post(
        "/api/v1/organizations/me/registration-code",
        json={},
        headers={
            "Authorization": (
                f"Bearer {login_response.json()['access_token']}"
            ),
        },
    )

    assert response.status_code == 403
    assert db_session.scalar(
        select(OrganizationRegistrationCode)
    ) is None


def test_database_allows_only_one_unrevoked_code_per_organization(
    db_session,
):
    organization, _, _ = create_registration_workspace(
        db_session,
        "registration-code-unique-org",
    )
    admin = User(
        organization_id=organization.id,
        email="registration-code-unique.admin@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Administrator",
    )
    db_session.add(admin)
    db_session.flush()
    db_session.add(
        OrganizationRegistrationCode(
            organization_id=organization.id,
            created_by_user_id=admin.id,
            code_hash="a" * 64,
        )
    )
    db_session.commit()
    db_session.add(
        OrganizationRegistrationCode(
            organization_id=organization.id,
            created_by_user_id=admin.id,
            code_hash="b" * 64,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_database_allows_only_one_unused_verification_token_per_user(
    db_session,
):
    organization = Organization(
        name="Verification Token Unique Organization",
        slug="verification-token-unique-organization",
    )
    db_session.add(organization)
    db_session.flush()
    user = User(
        organization_id=organization.id,
        email="verification-token-unique@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Verification Token User",
        lifecycle_managed=True,
        approval_status="pending",
        is_active=False,
    )
    db_session.add(user)
    db_session.flush()
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash="c" * 64,
            expires_at=expiration,
        )
    )
    db_session.commit()
    db_session.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash="d" * 64,
            expires_at=expiration,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_registration_code_validation_handles_expiry_and_rate_limit(
    client,
    db_session,
    monkeypatch,
):
    organization, _, _ = create_registration_workspace(
        db_session,
        "registration-expiry-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-expiry.admin@example.com",
    )
    code, _ = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    record = db_session.scalar(
        select(OrganizationRegistrationCode)
    )
    assert record is not None
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    expired_response = client.post(
        "/api/v1/auth/registration-code/validate",
        json={"code": code},
    )
    assert expired_response.status_code == 200
    assert expired_response.json() == {"valid": False}

    monkeypatch.setattr(
        "app.api.routes.auth.is_registration_ip_allowed",
        lambda key: False,
    )
    limited_response = client.post(
        "/api/v1/auth/registration-code/validate",
        json={"code": code},
    )
    assert limited_response.status_code == 429

    def unavailable(_key):
        raise RateLimitUnavailable

    monkeypatch.setattr(
        "app.api.routes.auth.is_registration_ip_allowed",
        unavailable,
    )
    unavailable_response = client.post(
        "/api/v1/auth/registration-code/validate",
        json={"code": code},
    )
    assert unavailable_response.status_code == 503


def test_registration_verification_is_separate_from_admin_approval(
    client,
    db_session,
    monkeypatch,
    email_service,
):
    allow_registration_rate_limits(monkeypatch)
    organization, branch, department = create_registration_workspace(
        db_session,
        "registration-flow-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-flow.admin@example.com",
    )
    code, admin_headers = create_admin_registration_code(
        client,
        db_session,
        admin,
    )

    registration_response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(code, branch.id, department.id),
    )

    assert registration_response.status_code == 202
    assert registration_response.json() == {
        "message": "If the information is eligible, your registration request was received.",
    }
    user = db_session.scalar(
        select(User).where(
            User.email == "new.employee@example.com",
        )
    )
    assert user is not None
    assert user.lifecycle_managed is True
    assert user.email_verified_at is None
    assert user.approval_status == "pending"
    assert user.is_active is False

    employee = db_session.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )
    assert employee is not None
    assert employee.organization_id == organization.id
    assert employee.branch_id == branch.id
    assert employee.department_id == department.id
    assert employee.is_active is False

    assert len(email_service.sent_emails) == 1
    email = email_service.sent_emails[0]
    assert email["recipient"] == user.email
    assert email["subject"] == "Verify your NexaWork email"
    token = verification_token_from_email(email)
    token_record = db_session.scalar(
        select(EmailVerificationToken)
    )
    assert token_record is not None
    assert token_record.token_hash != token
    assert len(token_record.token_hash) == 64

    verification_response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": token},
    )
    assert verification_response.status_code == 200
    db_session.refresh(user)
    db_session.refresh(employee)
    assert user.email_verified_at is not None
    assert user.approval_status == "pending"
    assert user.is_active is False
    assert employee.is_active is False
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 403
    approval_response = client.post(
        f"/api/v1/admin/employees/{user.id}/approve",
        headers=admin_headers,
    )
    assert approval_response.status_code == 200
    assert approval_response.json() == {
        "user_id": user.id,
        "approval_status": "approved",
        "is_active": True,
        "notification_status": "sent",
    }
    db_session.refresh(user)
    db_session.refresh(employee)
    assert user.is_active is True
    assert employee.is_active is True
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200
    assert email_service.sent_emails[-1]["subject"] == (
        "Your NexaWork registration was approved"
    )

    replay_response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": token},
    )
    assert replay_response.status_code == 400


def test_admin_pending_list_is_paginated_and_organization_scoped(
    client,
    db_session,
):
    organization, branch, department = create_registration_workspace(
        db_session,
        "approval-list-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "approval-list.admin@example.com",
    )
    _, admin_headers = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    other_organization, other_branch, other_department = (
        create_registration_workspace(
            db_session,
            "approval-list-other-org",
        )
    )
    other_admin = create_org_admin(
        db_session,
        other_organization,
        "approval-list-other.admin@example.com",
    )
    _, other_admin_headers = create_admin_registration_code(
        client,
        db_session,
        other_admin,
    )
    registrations = [
        create_pending_employee_registration(
            db_session,
            organization,
            branch,
            department,
            email=f"approval-list-{index}@example.com",
            employee_id=f"APP-LIST-{index}",
            verified=index != 1,
        )
        for index in range(3)
    ]
    create_pending_employee_registration(
        db_session,
        other_organization,
        other_branch,
        other_department,
        email="approval-list-other@example.com",
        employee_id="APP-LIST-OTHER",
        verified=True,
    )

    first_page = client.get(
        "/api/v1/admin/employees/pending?limit=1&offset=0",
        headers=admin_headers,
    )
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert len(first_page.json()["items"]) == 1
    assert first_page.json()["items"][0]["email_verified"] is True

    second_page = client.get(
        "/api/v1/admin/employees/pending?limit=1&offset=1",
        headers=admin_headers,
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1
    listed = client.get(
        "/api/v1/admin/employees/pending",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    listed_emails = {item["email"] for item in listed.json()["items"]}
    assert listed_emails == {
        "approval-list-0@example.com",
        "approval-list-1@example.com",
        "approval-list-2@example.com",
    }
    assert (
        client.get(
            "/api/v1/admin/employees/pending",
            headers=other_admin_headers,
        ).json()["total"]
        == 1
    )
    assert registrations[1][0].email in listed_emails


def test_admin_rejects_registration_and_rejected_list_preserves_reason(
    client,
    db_session,
    email_service,
):
    organization, branch, department = create_registration_workspace(
        db_session,
        "approval-reject-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "approval-reject.admin@example.com",
    )
    _, admin_headers = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    user, _ = create_pending_employee_registration(
        db_session,
        organization,
        branch,
        department,
        email="approval-reject@example.com",
        employee_id="APP-REJECT-001",
        verified=False,
    )

    response = client.post(
        f"/api/v1/admin/employees/{user.id}/reject",
        json={"reason": "Employment details could not be verified."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": user.id,
        "approval_status": "rejected",
        "is_active": False,
        "notification_status": "sent",
    }
    db_session.refresh(user)
    assert user.is_active is False
    assert user.approval_status == "rejected"

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "EMPLOYEE_REGISTRATION_REJECTED",
            AuditLog.resource_id == user.id,
        )
    )
    assert audit is not None
    assert audit.user_id == admin.id
    assert audit.details == "Employment details could not be verified."

    rejected_response = client.get(
        "/api/v1/admin/employees/rejected",
        headers=admin_headers,
    )
    assert rejected_response.status_code == 200
    assert rejected_response.json()["total"] == 1
    assert rejected_response.json()["items"][0]["rejection_reason"] == (
        "Employment details could not be verified."
    )
    assert rejected_response.json()["items"][0]["rejected_by"] == (
        "Organization Administrator"
    )
    assert email_service.sent_emails[-1]["subject"] == (
        "Your NexaWork registration update"
    )
    assert (
        "Employment details could not be verified."
        in email_service.sent_emails[-1]["body"]
    )
    assert client.post(
        f"/api/v1/admin/employees/{user.id}/reject",
        headers=admin_headers,
    ).status_code == 409


def test_admin_cannot_approve_unverified_or_cross_organization_registration(
    client,
    db_session,
):
    organization, branch, department = create_registration_workspace(
        db_session,
        "approval-scope-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "approval-scope.admin@example.com",
    )
    _, admin_headers = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    user, _ = create_pending_employee_registration(
        db_session,
        organization,
        branch,
        department,
        email="approval-scope@example.com",
        employee_id="APP-SCOPE-001",
        verified=False,
    )
    other_organization, other_branch, other_department = (
        create_registration_workspace(
            db_session,
            "approval-scope-other-org",
        )
    )
    other_user, _ = create_pending_employee_registration(
        db_session,
        other_organization,
        other_branch,
        other_department,
        email="approval-scope-other@example.com",
        employee_id="APP-SCOPE-OTHER",
        verified=True,
    )

    unverified_response = client.post(
        f"/api/v1/admin/employees/{user.id}/approve",
        headers=admin_headers,
    )
    assert unverified_response.status_code == 409
    cross_organization_response = client.post(
        f"/api/v1/admin/employees/{other_user.id}/approve",
        headers=admin_headers,
    )
    assert cross_organization_response.status_code == 404


def test_approval_is_committed_when_decision_email_delivery_fails(
    client,
    db_session,
    email_service,
    monkeypatch,
):
    organization, branch, department = create_registration_workspace(
        db_session,
        "approval-email-failure-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "approval-email-failure.admin@example.com",
    )
    _, admin_headers = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    user, _ = create_pending_employee_registration(
        db_session,
        organization,
        branch,
        department,
        email="approval-email-failure@example.com",
        employee_id="APP-EMAIL-FAILURE",
        verified=True,
    )

    def fail_delivery(**_message):
        raise EmailDeliveryUnavailable("delivery unavailable")

    monkeypatch.setattr(email_service, "send", fail_delivery)
    response = client.post(
        f"/api/v1/admin/employees/{user.id}/approve",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    assert response.json()["notification_status"] == "failed"
    db_session.refresh(user)
    assert user.is_active is True


def test_non_admin_cannot_list_or_decide_registrations(client, db_session):
    organization, branch, department = create_registration_workspace(
        db_session,
        "approval-forbidden-org",
    )
    user = User(
        organization_id=organization.id,
        email="approval-forbidden.member@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Organization Member",
    )
    db_session.add(user)
    db_session.commit()
    pending_user, _ = create_pending_employee_registration(
        db_session,
        organization,
        branch,
        department,
        email="approval-forbidden@example.com",
        employee_id="APP-FORBIDDEN-001",
        verified=True,
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "SecurePassword123!",
        },
    )
    headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}",
    }

    assert client.get(
        "/api/v1/admin/employees/pending",
        headers=headers,
    ).status_code == 403
    assert client.post(
        f"/api/v1/admin/employees/{pending_user.id}/approve",
        headers=headers,
    ).status_code == 403


def test_registration_rejects_invalid_code_and_cross_org_placement(
    client,
    db_session,
    monkeypatch,
):
    allow_registration_rate_limits(monkeypatch)
    organization, branch, department = create_registration_workspace(
        db_session,
        "registration-valid-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-valid.admin@example.com",
    )
    code, _ = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    other_org, other_branch, other_department = (
        create_registration_workspace(
            db_session,
            "registration-other-org",
        )
    )
    assert other_org.id != organization.id

    invalid_code = client.post(
        "/api/v1/auth/register",
        json=registration_payload(
            "invalid-registration-code",
            branch.id,
            department.id,
        ),
    )
    cross_org_placement = client.post(
        "/api/v1/auth/register",
        json=registration_payload(
            code,
            other_branch.id,
            other_department.id,
            email="cross.org@example.com",
            employee_id="EMP-CROSS-001",
        ),
    )

    assert invalid_code.status_code == 400
    assert "Organization" not in invalid_code.text
    assert cross_org_placement.status_code == 400
    assert "Organization" not in cross_org_placement.text
    assert db_session.scalar(
        select(User).where(User.email == "cross.org@example.com")
    ) is None


def test_duplicate_registration_response_does_not_disclose_email(
    client,
    db_session,
    monkeypatch,
    email_service,
):
    allow_registration_rate_limits(monkeypatch)
    organization, branch, department = create_registration_workspace(
        db_session,
        "registration-duplicate-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-duplicate.admin@example.com",
    )
    code, _ = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    payload = registration_payload(code, branch.id, department.id)

    first_response = client.post("/api/v1/auth/register", json=payload)
    first_email_count = len(email_service.sent_emails)
    duplicate_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 202
    assert duplicate_response.status_code == 202
    assert duplicate_response.json() == first_response.json()
    assert len(email_service.sent_emails) == first_email_count
    assert db_session.scalar(
        select(User).where(User.email == payload["email"])
    ) is not None


def test_email_delivery_failure_is_logged_without_email_enumeration(
    client,
    db_session,
    monkeypatch,
    email_service,
    caplog,
):
    from app.services.email.service import EmailDeliveryUnavailable

    allow_registration_rate_limits(monkeypatch)
    organization, branch, department = create_registration_workspace(
        db_session,
        "registration-mail-failure-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-mail-failure.admin@example.com",
    )
    code, _ = create_admin_registration_code(
        client,
        db_session,
        admin,
    )

    def fail_sending(**kwargs):
        raise EmailDeliveryUnavailable("provider outage")

    monkeypatch.setattr(email_service, "send", fail_sending)
    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(code, branch.id, department.id),
    )

    assert response.status_code == 202
    assert "delivery failed" in caplog.text
    assert "new.employee@example.com" not in caplog.text
    assert db_session.scalar(
        select(User).where(User.email == "new.employee@example.com")
    ) is not None


def test_resend_verification_is_non_enumerating_and_rotates_token(
    client,
    db_session,
    monkeypatch,
    email_service,
):
    allow_registration_rate_limits(monkeypatch)
    organization, branch, department = create_registration_workspace(
        db_session,
        "registration-resend-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-resend.admin@example.com",
    )
    code, _ = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    client.post(
        "/api/v1/auth/register",
        json=registration_payload(code, branch.id, department.id),
    )
    first_record = db_session.scalar(
        select(EmailVerificationToken)
    )
    assert first_record is not None

    existing_response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "new.employee@example.com"},
    )
    missing_response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "missing@example.com"},
    )

    assert existing_response.status_code == 202
    assert missing_response.status_code == 202
    assert existing_response.json() == missing_response.json()
    assert first_record.used_at is not None
    assert len(email_service.sent_emails) == 2
    old_token = verification_token_from_email(email_service.sent_emails[0])
    assert client.post(
        "/api/v1/auth/verify-email",
        json={"token": old_token},
    ).status_code == 400


def test_verification_rejects_expired_token(client, db_session, email_service):
    organization, branch, department = create_registration_workspace(
        db_session,
        "registration-expired-org",
    )
    admin = create_org_admin(
        db_session,
        organization,
        "registration-expired.admin@example.com",
    )
    code, _ = create_admin_registration_code(
        client,
        db_session,
        admin,
    )
    client.post(
        "/api/v1/auth/register",
        json=registration_payload(code, branch.id, department.id),
    )
    token_record = db_session.scalar(
        select(EmailVerificationToken)
    )
    assert token_record is not None
    token_record.expires_at = datetime.now(timezone.utc) - timedelta(
        minutes=1,
    )
    db_session.commit()
    token = verification_token_from_email(email_service.sent_emails[0])

    response = client.post(
        "/api/v1/auth/verify-email",
        json={"token": token},
    )

    assert response.status_code == 400
