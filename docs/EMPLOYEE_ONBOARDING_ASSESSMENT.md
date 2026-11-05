# Employee onboarding implementation assessment

## Implementation status

The backend lifecycle and first frontend pass are now implemented:

- Alembic migration `d9e1a4b7c230` adds the lifecycle columns and three tenant-scoped onboarding tables.
- Registration codes can be created, listed without revealing their value, rotated, and revoked.
- Public registration resolves active branches/departments from a valid code, and email verification is required before approval. Verification links expire after 24 hours and can be resent without disclosing whether a request exists.
- Invitations support creation, resend, revoke, expiry, and one-time acceptance.
- Admin onboarding screens cover pending/rejected requests, invitation status, registration codes, and employee enable/disable actions.
- Administrative lifecycle changes are written to the existing immutable audit log. Disable actions invalidate existing JWTs.
- Public onboarding endpoints use the existing Redis-backed IP rate limiter.

Local development defaults to the fake email service. Real delivery is available through the configurable SMTP email service; set `EMAIL_PROVIDER=smtp`, `SMTP_HOST`, and `SMTP_FROM_EMAIL`, then provide SMTP credentials through the deployment secret manager when required. SMTP authentication requires TLS. Production rejects the fake provider and requires TLS. Invitation, verification, approval and recovery messages use the host from `PASSWORD_RESET_URL`. Delivery failures are surfaced to the request caller; because onboarding state is committed before the email is sent, failed invitation sends can be retried from Onboarding.

## 1. Existing capabilities that can be reused

- Organization creation and tenant boundaries already exist in `app/api/routes/organizations.py` and `app/models/organization.py`.
- User, employee, branch, department, and team models are already present and can anchor onboarding flows.
- JWT auth, role checks, and `ADMIN_ACCESS` enforcement are available in `app/api/dependencies.py`.
- Rate limiting and Redis protection exist for auth and messaging and can be reused for registration attempts.
- Email delivery is abstracted via `app/services/email/service.py`, with a fake implementation already in place for local testing.
- Audit logging is already implemented in `app/models/audit_log.py` and is the right place to record lifecycle decisions.

## 2. Original missing functionality

- Organization registration codes for employee self-registration were not present.
- Pending employee registration and approval workflow did not exist.
- Invitation lifecycle and acceptance flow did not exist.
- Distinct email-verification, approval, and account-status states were not modeled separately.
- Disable and re-enable employee actions were not implemented end-to-end.

## 3. Required database changes

- New table for organization registration codes.
- New table for employee registration requests.
- New table for employee invitations.
- New fields on `Employee` to hold email verification, approval, and account status separately.

## 4. Required backend changes

- Add onboarding routes and service layer for registration codes, self-registration, admin approval, invitations, resending, revocation, verification, and enable/disable actions.
- Enforce organization-scoped validation and permission checks.
- Use a hashed password flow and safe token generation.
- Add audit-friendly lifecycle state transitions.

## 5. Required frontend changes

- Add a public registration page that accepts organization registration code and user details.
- Add admin dashboard views for pending approvals, invitation management, active employees, disabled employees, and rejected requests.
- Add account lifecycle UI for disable/reenable flows and full employee management.

## 6. Security risks and mitigation

- Registration code leakage: keep codes server-side and validate without exposing organization internals.
- Duplicate or conflicting approvals: enforce one pending state and a single approval path.
- Token replay and stale invites: use one-time tokens with expiry and status checks.
- Privilege escalation: restrict all lifecycle routes to admin or permission-bound access.
- Inactive and disabled accounts: revoke token validity and block login before permission is restored.

## 7. Original proposed implementation order

1. Add the database-backed onboarding models.
2. Add registration-code and self-registration flows.
3. Add admin approval/rejection flows.
4. Add invitation creation, resend, revoke, and acceptance flows.
5. Add disable and re-enable account operations.
6. Add targeted backend tests to validate lifecycle transitions.
7. Follow with frontend screens and dashboard integration.

## 8. Remaining production work

- Replace `FakeEmailService` with a configured delivery provider and verify delivery/retry behavior.
- Run the Alembic migration against the deployment database and review the generated schema there.
- Run the Python and frontend test suites in an environment with the repository dependencies installed.
- Consider storing only digests for invitation and registration tokens before onboarding is exposed to production traffic.
