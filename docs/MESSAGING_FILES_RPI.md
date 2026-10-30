# Messaging and files — RPI implementation record

Base: main f808143084421600c414e182a75f2e1ba63c8034. Required brief: Pasted markdown(7).md; detailed read-only plan supplied in this chat. Risk: critical (tenant file privacy). No production migration, provisioning or release is authorized by this implementation.

## Research and plan

Observed: text conversations/messages already enforce active org members, message history uses an ID cursor; conversation listing is capped without continuation. Main includes milestone-0 test discovery repair. No attachment backend or messaging frontend exists. React/TypeScript/Vite, existing navy/blue semantic tokens, memory-only bearer sessions and thin FastAPI routes are retained.

Slices: (1) compatible conversation paging and member directory; (2) private attachment lifecycle and atomic/idempotent message binding; (3) conversation workspace and Files view; (4) targeted tests and review. No new frontend dependency. Binary upload uses one raw request body and an encoded filename header rather than multipart, avoiding whole-file JSON/base64 and a new multipart parser. Existing v1 array response remains; new page endpoint supplies an envelope and member names.

Acceptance: create direct/group, traverse conversations and older messages, upload bounded validated files, send captions with up to ten attachments, list/download only as an active conversation member, abandon/delete safely, preserve text-only API, handle session expiry/errors/retries without duplicate sends. No unsafe HTML rendering; no signed/public file URLs. Responsive master/detail with explicit mobile back navigation, accessible labels and keyboard controls. Identity: welcoming, assured, organized; existing tokens and icons.

Storage: local private storage is the initial adapter for a single persistent host/development; its production use requires an explicit persistent-storage acknowledgement and configured ClamAV. No storage provider or bucket is silently provisioned. Uploads default off until configured. Scanner bypass is development/test only and does not claim malware safety. Object storage adapter remains a follow-on deployment option. Files are served as downloads with no-store/nosniff; never previewed inline.

Threats: cross-org/IDOR → query scopes + composite FKs; other user's draft → owner-only visibility/binding; malformed file/path → safe name, generated key, size/content policy; stale auth → final recheck and locked binding; retries → scoped client message key; orphan objects → reserved metadata and expiry cleanup; byte exposure → private root, scanner gate, authorized stream; audit → immutable existing records plus attributable user operations. In-flight bytes cannot be recalled. Exact commit-order synchronization is not promised by polling.

Verification and remaining limits are recorded after implementation. Full production retention/legal-hold policy, external object storage and multi-host operation require a separate deployment decision. Attached content is not automatically expired; abandoned drafts expire after 24h. Deletion hides immediately and bytes are purged by the cleanup command. Audit rows are never deleted.

## Verification record — local implementation

PASS: 81 selected backend tests and seven subtests in an explicitly diagnostic Python 3.14 environment; 21 frontend tests; TypeScript/Vite production build; frontend format check; Python compilation; OpenAPI raw-binary request documentation; Git whitespace/diff check; static single-head migration graph. An inline ASGI diagnostic additionally passed 26 assertions using real password/JWT authentication, routes, services and FK-enabled SQLite. Only scheduling and external Redis/scanner test seams were substituted; it is not concurrency or pinned-runtime evidence.

Interface Forge and the React review checklist guided the existing-brand UI: semantic controls, responsive master/detail, visible focus, separate draft state, request cancellation, bounded paging, lazy loading and explicit error/disabled states. The built messaging chunk is approximately 19.36 kB / 6.47 kB gzip. No production latency or accessibility conformance claim is made.

BLOCKED/NOT RUN: pinned Python 3.12 full HTTP suite (package-host resolution unavailable; fallback TestClient also hangs with an empty app), real browser/visual/mobile flows (sandbox denies local server listeners), PostgreSQL migration/race execution, real ClamAV/Redis integration, load tests and dependency audit. PostgreSQL race and normal API tests are authored for isolated CI. No assertions or production controls were disabled to obtain a pass. At the time of local verification, no migration, production infrastructure change, remote commit/push or deployment had occurred. This record accompanies subsequent PR publication; it does not certify a deployment.

Release status: NOT RELEASE READY until these gates, persistent storage/scanner setup and retention/operator decisions are verified. The private single-host local adapter is the initial implementation; S3/multi-host storage remains a follow-on deployment adapter. Keep uploads off until configured; audit mutation protections remain unchanged.
