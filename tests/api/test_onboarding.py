from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from app.core.security.password import hash_password
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.audit_log import AuditLog
from app.models.employee_registration import EmployeeRegistrationRequest
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.region import Region
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.models.user import User
from app.models.user_role import user_roles
from app.schemas.onboarding import EmployeeInvitationResponse


def _create_admin(
    client,
    db_session,
    organization,
    email="admin.onboarding@example.com",
):
    admin_user = User(
        organization_id=organization.id,
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        full_name="Admin User",
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.flush()

    permission = db_session.scalar(
        select(Permission).where(Permission.name == "ADMIN_ACCESS")
    )
    if permission is None:
        permission = Permission(
            name="ADMIN_ACCESS",
            description="Admin access",
        )
        db_session.add(permission)
        db_session.flush()

    role = Role(
        organization_id=organization.id,
        name="Workspace Admin",
        description="Access onboarding admin routes",
        is_active=True,
    )
    db_session.add(role)
    db_session.flush()

    db_session.execute(
        role_permissions.insert().values(
            role_id=role.id,
            permission_id=permission.id,
        )
    )
    db_session.execute(
        user_roles.insert().values(
            user_id=admin_user.id,
            role_id=role.id,
        )
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": admin_user.email,
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def test_registration_code_and_self_registration_flow(
    client,
    db_session,
    email_service,
):
    organization = Organization(name="Onboarding Org", slug="onboarding-org")
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="North Region",
        slug="north-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="HQ Branch",
        slug="hq-branch",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Engineering",
        slug="engineering",
    )
    db_session.add(department)
    db_session.flush()

    token = _create_admin(client, db_session, organization)

    code_response = client.post(
        "/api/v1/onboarding/registration-codes",
        headers={"Authorization": f"Bearer {token}"},
        json={"expires_in_minutes": 60},
    )
    assert code_response.status_code == 201
    code = code_response.json()["code"]

    structure_response = client.post(
        "/api/v1/onboarding/registration-structure",
        json={"registration_code": code},
    )
    assert structure_response.status_code == 200
    assert structure_response.json()["branches"][0]["id"] == branch.id
    assert (
        structure_response.json()["branches"][0]["departments"][0]["id"]
        == department.id
    )

    registration_response = client.post(
        "/api/v1/onboarding/register",
        json={
            "full_name": "Jane Employee",
            "email": "jane.employee@example.com",
            "password": "SecurePassword123!",
            "job_title": "Developer",
            "branch_id": branch.id,
            "department_id": department.id,
            "registration_code": code,
        },
    )
    assert registration_response.status_code == 201
    payload = registration_response.json()
    assert payload["approval_status"] == "pending"
    assert payload["email_verification_status"] == "unverified"

    unverified_approval = client.post(
        f"/api/v1/onboarding/requests/{payload['id']}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert unverified_approval.status_code == 400

    verification_link = email_service.sent_emails[-1]["body"].rsplit(" ", 1)[-1]
    verification_token = parse_qs(urlsplit(verification_link).query)["token"][0]
    registration_request = db_session.get(
        EmployeeRegistrationRequest,
        payload["id"],
    )
    assert registration_request is not None
    registration_request.verification_expires_at = datetime.now(
        timezone.utc
    ) - timedelta(seconds=1)
    db_session.commit()
    expired_verification = client.post(
        "/api/v1/onboarding/verify-email",
        json={"token": verification_token},
    )
    assert expired_verification.status_code == 400

    resend_response = client.post(
        "/api/v1/onboarding/resend-verification",
        json={
            "registration_code": code,
            "email": "jane.employee@example.com",
        },
    )
    assert resend_response.status_code == 200
    assert "matching registration request" in resend_response.json()["message"]
    verification_link = email_service.sent_emails[-1]["body"].rsplit(" ", 1)[-1]
    resent_token = parse_qs(urlsplit(verification_link).query)["token"][0]
    assert resent_token != verification_token
    verification_response = client.post(
        "/api/v1/onboarding/verify-email",
        json={"token": resent_token},
    )
    assert verification_response.status_code == 200
    assert (
        verification_response.json()["email_verification_status"] == "verified"
    )

    request_id = payload["id"]
    approval_response = client.post(
        f"/api/v1/onboarding/requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Approved for onboarding"},
    )
    assert approval_response.status_code == 200
    approved = approval_response.json()
    assert approved["approval_status"] == "approved"
    assert approved["employee_id"]
    assert approved["employee_id"] in email_service.sent_emails[-1]["body"]
    assert "password you chose" in email_service.sent_emails[-1]["body"]

    user = db_session.scalar(
        select(User).where(User.email == "jane.employee@example.com")
    )
    assert user is not None
    employee = db_session.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )
    assert employee is not None
    assert employee.approval_status == "approved"
    assert employee.employee_id == approved["employee_id"]

    listed_requests = client.get(
        "/api/v1/onboarding/requests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed_requests.status_code == 200
    assert listed_requests.json()[0]["employee_id"] == employee.employee_id

    listed_employees = client.get(
        "/api/v1/onboarding/employees",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed_employees.status_code == 200
    assert listed_employees.json()[0]["employee_id"] == employee.employee_id

    employee_login = client.post(
        "/api/v1/auth/employee/login",
        json={
            "employee_id": employee.employee_id,
            "password": "SecurePassword123!",
        },
    )
    assert employee_login.status_code == 200
    assert employee_login.json()["employee_id"] == employee.employee_id
    assert db_session.scalar(
        select(AuditLog.id).where(
            AuditLog.action == "onboarding.registration_code.created"
        )
    )
    assert db_session.scalar(
        select(AuditLog.id).where(
            AuditLog.action == "onboarding.registration_request.approved"
        )
    )


def test_registration_code_can_be_rotated_and_revoked(client, db_session):
    organization = Organization(name="Code Org", slug="code-org")
    db_session.add(organization)
    db_session.flush()
    token = _create_admin(client, db_session, organization)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/v1/onboarding/registration-codes",
        headers=headers,
        json={"expires_in_minutes": 60},
    )
    assert created.status_code == 201
    old_code = created.json()["code"]

    listed = client.get(
        "/api/v1/onboarding/registration-codes",
        headers=headers,
    )
    assert listed.status_code == 200
    assert "code" not in listed.json()[0]

    rotated = client.post(
        f"/api/v1/onboarding/registration-codes/{created.json()['id']}/rotate",
        headers=headers,
        json={"expires_in_minutes": 60},
    )
    assert rotated.status_code == 201
    assert rotated.json()["code"] != old_code
    assert rotated.json()["is_active"] is True

    revoked = client.post(
        f"/api/v1/onboarding/registration-codes/{rotated.json()['id']}/revoke",
        headers=headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False
    assert revoked.json()["revoked_at"] is not None

    other_organization = Organization(
        name="Other Code Org",
        slug="other-code-org",
    )
    db_session.add(other_organization)
    db_session.flush()
    other_token = _create_admin(
        client,
        db_session,
        other_organization,
        email="other-admin.onboarding@example.com",
    )
    cross_tenant_revoke = client.post(
        f"/api/v1/onboarding/registration-codes/{created.json()['id']}/revoke",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert cross_tenant_revoke.status_code == 400


def test_invitation_acceptance_creates_employee_and_consumes_link(
    client,
    db_session,
    email_service,
):
    organization = Organization(name="Invite Org", slug="invite-org")
    db_session.add(organization)
    db_session.flush()
    region = Region(
        organization_id=organization.id,
        name="West Region",
        slug="west-region",
    )
    db_session.add(region)
    db_session.flush()
    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="West Branch",
        slug="west-branch",
    )
    db_session.add(branch)
    db_session.flush()
    department = Department(
        branch_id=branch.id,
        name="Support",
        slug="support",
    )
    db_session.add(department)
    db_session.flush()
    token = _create_admin(client, db_session, organization)

    response = client.post(
        "/api/v1/onboarding/invitations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Invited Employee",
            "email": "invited@example.com",
            "job_title": "Support Specialist",
            "branch_id": branch.id,
            "department_id": department.id,
        },
    )
    assert response.status_code == 201
    invitation_link = email_service.sent_emails[-1]["body"].rsplit(" ", 1)[-1]
    assert response.json()["acceptance_url"] == invitation_link
    invitation_token = parse_qs(urlsplit(invitation_link).query)["token"][0]

    assert "acceptance_url" not in EmployeeInvitationResponse.model_fields
    resent = client.post(
        f"/api/v1/onboarding/invitations/{response.json()['id']}/resend",
        headers={"Authorization": "Bearer " + token},
    )
    assert resent.status_code == 200
    resent_link = resent.json()["acceptance_url"]
    assert resent_link != invitation_link
    assert email_service.sent_emails[-1]["body"].endswith(resent_link)
    resent_token = parse_qs(urlsplit(resent_link).query)["token"][0]

    accepted = client.post(
        "/api/v1/onboarding/invitations/accept",
        json={
            "token": resent_token,
            "password": "SecurePassword123!",
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["employee_id"]
    assert "employee_id" not in EmployeeInvitationResponse.model_fields
    assert "invitation_token" not in accepted.json()
    assert db_session.scalar(
        select(User).where(User.email == "invited@example.com")
    )

    replayed = client.post(
        "/api/v1/onboarding/invitations/accept",
        json={
            "token": resent_token,
            "password": "SecurePassword123!",
        },
    )
    assert replayed.status_code == 400
    expired_link = client.post(
        "/api/v1/onboarding/invitations/accept",
        json={
            "token": invitation_token,
            "password": "SecurePassword123!",
        },
    )
    assert expired_link.status_code == 400


def test_employee_disable_and_enable_flow(client, db_session):
    organization = Organization(name="Lifecycle Org", slug="lifecycle-org")
    db_session.add(organization)
    db_session.flush()

    region = Region(
        organization_id=organization.id,
        name="South Region",
        slug="south-region",
    )
    db_session.add(region)
    db_session.flush()

    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Branches",
        slug="branches",
    )
    db_session.add(branch)
    db_session.flush()

    department = Department(
        branch_id=branch.id,
        name="Operations",
        slug="operations",
    )
    db_session.add(department)
    db_session.flush()

    admin_token = _create_admin(client, db_session, organization)

    employee_user = User(
        organization_id=organization.id,
        email="employee.lifecycle@example.com",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Lifecycle Employee",
        is_active=True,
    )
    db_session.add(employee_user)
    db_session.flush()

    employee = Employee(
        organization_id=organization.id,
        user_id=employee_user.id,
        employee_id="NEXA-1-00001",
        branch_id=branch.id,
        department_id=department.id,
        job_title="Operations Lead",
        profile_picture=None,
        is_active=True,
        email_verification_status="verified",
        approval_status="approved",
        account_status="active",
    )
    db_session.add(employee)
    db_session.commit()
    employee_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": employee_user.email,
            "password": "SecurePassword123!",
        },
    )
    assert employee_login.status_code == 200
    employee_headers = {
        "Authorization": f"Bearer {employee_login.json()['access_token']}",
    }

    disable_response = client.post(
        f"/api/v1/onboarding/employees/{employee.id}/disable",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Suspended for review"},
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["account_status"] == "disabled"

    employee_user_after = db_session.get(User, employee_user.id)
    assert employee_user_after.is_active is False
    assert client.get(
        "/api/v1/auth/me",
        headers=employee_headers,
    ).status_code == 401

    enable_response = client.post(
        f"/api/v1/onboarding/employees/{employee.id}/enable",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["account_status"] == "active"
    assert client.get(
        "/api/v1/auth/me",
        headers=employee_headers,
    ).status_code == 401
