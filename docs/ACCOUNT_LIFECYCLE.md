# Employee account lifecycle foundation

This document describes the account-state foundation added in Milestone 1. It
does not imply that self-registration, invitation, or admin dashboard flows are
available yet.

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
- Changing the email of a lifecycle-managed account clears verification,
  disables the account, and increments `token_version`.

The state-transition services are not exposed as new public API endpoints in
this milestone. Future routes must also enforce the existing RBAC permissions
and tenant authorization.

## Migration and rollback

Migration `a91d4e6c2f80` adds the state fields and constraints. Its downgrade
drops those fields and therefore loses lifecycle state. Do not downgrade after
lifecycle-managed accounts have been created unless their state has been
preserved through an approved recovery plan.

Email verification tokens, registration codes, invitation records, public
registration, approval endpoints, notifications, and dashboard integration
remain future milestones.
