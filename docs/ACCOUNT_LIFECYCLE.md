# Employee account lifecycle foundation

This document describes the account-state foundation and self-registration
backend added in Milestones 1 and 2. It does not imply that invitation or admin
dashboard flows are available yet.

## Separate account states

| Concern | User field | Meaning |
| --- | --- | --- |
| Email verification | `email_verified_at` | `NULL` means unverified; a timestamp means verified. |
| Registration approval | `approval_status` | `pending`, `approved`, or `rejected`. |
| Account access | `is_active` | Whether the account may authenticate. |
| Lifecycle enforcement | `lifecycle_managed` | Enables onboarding state checks for newly onboarded accounts. |

Existing accounts remain `lifecycle_managed = false`, default to `approved`,
and keep `email_verified_at = NULL`. This preserves existing login behavior
without claiming those email addresses were verified. New onboarding flows must
set `lifecycle_managed = true` and explicitly create an inactive account in
the appropriate approval state.

The database rejects an active lifecycle-managed account unless its email is
verified and approval is `approved`. Lifecycle-managed super-admin accounts
are disallowed. `Employee.is_active` remains a separate employment-record flag;
it is not a substitute for disabling the linked user account.

## Implemented transition rules

- Email verification is recorded once and rejected registrations cannot be
  verified.
- Approval requires a verified email, a pending registration, and a different
  active actor in the same organization. Rejection is terminal.
- Approval activates the verified account; rejection keeps it inactive. Both
  decisions increment `token_version` and write an audit event.
- Enabling a lifecycle-managed account requires approved status and verified
  email. Changes to account activation increment `token_version`, so tokens
  issued before disable/re-enable remain invalid.
- Email changes for lifecycle-managed accounts are rejected until a dedicated
  reverification flow is available.

Milestone 2 adds these self-registration endpoints:

- `POST /api/v1/organizations/me/registration-code` creates or rotates an
  organization code. The plaintext value is returned only at creation.
- `DELETE /api/v1/organizations/me/registration-code` revokes the active code.
- `POST /api/v1/auth/registration-code/validate` returns only `valid: true` or
  `valid: false`; it never returns organization details.
- `POST /api/v1/auth/register` creates a pending, inactive user and employee
  after validating the code and same-organization branch/department placement.
- `POST /api/v1/auth/verify-email` consumes a one-time verification token.
- `POST /api/v1/auth/resend-verification` replaces an outstanding token while
  returning a non-enumerating response.

The registration-code management routes require the existing organization
admin authentication and `ADMIN_ACCESS`. Public registration and verification
remain separate from approval; a verified registration stays inactive and
pending until the admin-approval milestone.

Registration codes and email verification tokens are stored as SHA-256
digests. Codes default to a 30-day expiry (administrators may select 1–365
days or no expiry), and verification tokens expire after the configured
`EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES`. Registration, code validation, and
verification resend use IP and/or hashed identity/code rate limits.

`EMAIL_PROVIDER=fake` is allowed only in development/test and stores messages
in process memory. Other environments use `EMAIL_PROVIDER=unconfigured`;
registration and password recovery return 503 before processing until a real
email provider is configured. A configured provider's transient verification
send failures are logged without recipient/token data; the registration
remains pending and can request a replacement token.

## Migration and rollback

Migration `a91d4e6c2f80` adds the state fields and constraints. Its downgrade
drops those fields and therefore loses lifecycle state. Do not downgrade after
lifecycle-managed accounts have been created unless their state has been
preserved through an approved recovery plan.

Migration `b52d10e7a4c9` adds registration-code and email-verification-token
storage; its downgrade drops those records and invalidates outstanding codes
and links.

Invitations, admin approval APIs, notifications for approval outcomes, and
dashboard/frontend integration remain future milestones.
