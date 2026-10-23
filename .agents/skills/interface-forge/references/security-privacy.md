# Interface security, privacy and trust

Visual polish does not compensate for incorrect authority, misleading account states, data leakage or unsafe interactions.

## Non-negotiable

- Authorization enforced server-side. Hidden buttons are **not** access control; UI should still reflect permission states clearly.
- No secrets or privileged tokens in client bundles; never copy `.env` contents into design documents or bug reports.
- Escape untrusted content; avoid unsafe `dangerouslySetInnerHTML`/raw HTML. Sanitize with battle-tested tools only when rich HTML is required.
- Validate uploads server-side (MIME/content, size, extension, storage, malware scanning as appropriate), even when client-side validation exists.
- Prevent accidental destructive actions, double submits and misleading confirmations; distinguish optimistic UI from settled truth.
- Avoid displaying financial/personal records in logs, analytics, screenshots, synthetic sample apps or third-party effect telemetry without authorization.
- Guard external redirects/links, CSRF/session handling and user-input injection as appropriate to stack.
- Third-party libraries and fonts/assets: evaluate origin, version pinning, advisories, license, data flow, tracking behavior and fallback.

## Trust-oriented patterns

For finance/reconciliation and similar products: explicit monetary units, transaction identifiers masked where needed, data freshness timestamps, source provenance, open discrepancies, uncertainty, audit trail, approval authority, and reversible investigation actions. No invented final balances, made-up proof or resolution percentages. Use confirmation of server state before communicating settlement or closure.

For health/other sensitive data: minimize exposed details, distinguish authoritative information from interpretation, guard shared devices, respect role scoping and avoid personally identifiable examples.

## Review checklist

- [ ] No apparent privilege escalation disguised as UI enhancement
- [ ] Sensitive data not injected into public/client telemetry
- [ ] Relevant forms and uploads have appropriate safeguards
- [ ] Actions and error messages do not imply false completion
- [ ] Third-party sources/licenses reviewed before install
- [ ] Actual auth/API behavior tested, or explicitly unverified
