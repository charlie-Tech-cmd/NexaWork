# NexaWork messaging and file sharing — implementation review

Implemented locally using the repository's RPI and Interface Forge workflows. Base: main `f808143084421600c414e182a75f2e1ba63c8034` (PR #7 is merged). Local branch: `feat/messaging-and-private-files`. The source tree and base commit were verified against GitHub; this record captures local verification before PR publication. No production deployment or migration was performed.

## Review materials

See MESSAGING_FILES_PLAN.md, MESSAGING_FILES_RPI.md and MESSAGING_FILES_SETUP.md. Local check logs are reproduced below; they are historical evidence, not CI results.

## Implemented behavior

Messages and Files are integrated into the existing React workspace and its navy/blue design system. Members can find colleagues, create direct/group conversations, traverse conversation pages and older history, send messages, and share/download multiple attachments with a caption. Drafts and retry identifiers stay separate by conversation in memory. Requests are cancelled on unmount; session expiry signs out. Loading, empty, failure, retry, unavailable-file and deletion states are explicit.

The backend adds a tenant-scoped attachment lifecycle, raw bounded binary receipt, generated private storage keys, filename/size/content checks, a ClamAV scan gate, atomic attachment binding, UUID-based message retry protection, immutable user audit events, metadata/download/delete APIs and cleanup. Drafts are private to their uploader. Downloads require current membership; cross-tenant IDs do not authorize access. Deletion hides immediately and preserves tombstones/audit history while cleanup removes bytes. Existing audit protections are unchanged.

Efficiency comes from cursor paging, batched metadata/member queries, bounded file streams, short database transactions, serialized quota reservations, and nonoverlapping visible/online polling. The messaging UI is lazy-loaded: its JS chunk is 19.36 kB (6.47 kB gzip). No production throughput or latency claim is made.

The existing conversation-array API remains an array with optional continuation; a new envelope endpoint supports the UI. Text remains nonblank; file-only messages, websocket delivery, presence, read receipts and message editing/deletion are outside this slice. File storage currently supports one persistent host behind a streaming adapter; S3/multi-host deployment remains a separate adapter decision.

## Actual verification

| Check | Result | Scope |
| --- | --- | --- |
| Targeted backend suite | **81 passed**, seven subtests passed | Services, file validation/storage, FK-enabled SQLite constraints, audit immutability, rate-limit failures, scanner protocol, disconnect cleanup and production configuration guards. Diagnostic Python 3.14 environment. |
| Frontend tests | **21 passed** | Existing and new API/client, paging merge, upload checks, retry and session-expiry behavior. |
| Inline ASGI diagnostic | **26 assertions passed** | Real password/JWT auth, routes, schemas, services and FK-enabled SQLite: upload → bind/send → retry → authorized download → delete, with cross-tenant and invalid-input denials. |
| Production frontend build/typecheck | **PASS** | React/TypeScript/Vite; separate lazy messaging chunk. |
| Frontend formatting | **PASS** | Existing Prettier check. |
| Python compilation / OpenAPI | **PASS** | Raw binary request documented without reading the whole file as a framework bytes parameter. |
| Patch and migration graph | **PASS, static** | Patch applies cleanly and reproduces changed files; one migration head `ab921ed70431`. No database upgrade executed. |

Backend runtime limitations matter: the pinned Python 3.12 environment could not be installed because command-line package-host resolution failed. Recovered cached/official packages allowed a diagnostic Python 3.14 run, with several library versions differing from the pins. Normal TestClient startup hung even for an empty FastAPI application. The ASGI diagnostic used inline scheduling to avoid that restriction and the same external rate-limit test seam as existing fixtures; scanning used the explicit development-only bypass. It is **not** evidence of real HTTP scheduling, PostgreSQL races, Redis, a live scanner or production performance. The diagnostic harness is provided for inspection; run it only from the repository root with nonproduction settings and isolated dependencies.

The environment also denied local server listeners with EPERM, preventing real-browser desktop/mobile, visual, accessibility and upload/download QA. No screenshot or accessibility-conformance claim is fabricated. Normal API and opt-in disposable PostgreSQL race tests are authored in the source for CI, but were not executed here. Dependency audit, production-volume/backup tests and load testing were not run.

Logs: backend, frontend tests, build, format, API diagnostic.

## Release status and next action

**NOT RELEASE READY yet.** The code is prepared for review; it is not live on the existing website. Before enabling files, run the pinned full API suite, PostgreSQL migration/constraint/race checks, real scanner/Redis tests and browser flows in an environment that permits them. Apply the additive migration through an approved deployment process before deploying this server. Configure private persistent storage, a private maintained scanner, Redis protection, cleanup, capacity limits and retention/backup ownership. The setup guide records exact settings and rollout/rollback order.

Uploads default to disabled. Production rejects the scan bypass and rejects enabled files without persistent-storage acknowledgement, scanner configuration and rate limits. File signatures/scanning are layered defenses, not proof that arbitrary PDF/image content is harmless; no inline preview is provided. Keep attached-content retention and any system-actor requirements under explicit review.

No live database, Supabase database, real user data, production migration, credentials, bucket, cloud service, privileges, merge or infrastructure was changed.

## Local verification logs

### backend-checks

```text
<frozen site>:107: RuntimeWarning: Unexpected value in sys.prefix, expected WORKSPACE/work/backend-venv, got REPOSITORY/../backend-venv
<frozen site>:107: RuntimeWarning: Unexpected value in sys.exec_prefix, expected WORKSPACE/work/backend-venv, got REPOSITORY/../backend-venv
................................................................. [ 80%]
................                                                         [100%]
=============================== warnings summary ===============================
../backend-venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  WORKSPACE/work/backend-venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
81 passed, 1 warning, 7 subtests passed in 6.39s

```

### frontend-tests

```text

> nexawork-frontend@0.1.0 test
> node --experimental-strip-types --test --test-isolation=none tests/*.test.ts

✔ authenticated writes send bearer token and JSON without cookies (25.733202ms)
✔ 403 remains a permission error (1.427709ms)
✔ 401 preserves status for session expiry handling (0.588132ms)
✔ validation errors identify fields without exposing submitted values (0.686678ms)
✔ server errors conceal exception details (0.482462ms)
✔ network failure offers recovery (0.302853ms)
✔ malformed successful responses are rejected (0.654768ms)
✔ empty success responses are supported (0.246265ms)
✔ hierarchy matches backend paths and team payload (0.350192ms)
✔ external URLs cannot receive credentials (0.30176ms)
✔ public URLs resolve to distinct onboarding, login, and protected workspace views (0.233622ms)
✔ reset token is extracted from the email link query string (0.225035ms)
✔ trailing slashes are accepted without mistaking unrelated routes for auth (0.210447ms)
✔ responsive office assets are real JPEGs under the per-image budget (4.906226ms)
✔ history pages merge without duplicates and update existing messages in ID order (0.284407ms)
✔ direct titles exclude the current member; groups use their name (0.228903ms)
✔ client file checks reject disabled, empty, oversized, unsupported and excessive files (0.672071ms)
✔ conversation cursors are encoded and sent only to the fixed API route (0.541994ms)
✔ uploads send raw binary with encoded filename, no cookies or redirects (0.662663ms)
✔ retry sends keep the same client message identifier and attachment IDs (0.675818ms)
✔ binary session expiry signs out, provider internals stay hidden (0.518421ms)
ℹ tests 21
ℹ suites 0
ℹ pass 21
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 101.565315

```

### frontend-build

```text

> nexawork-frontend@0.1.0 build
> tsc --noEmit && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 35 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                       0.75 kB │ gzip:  0.42 kB
dist/assets/Messaging-CWUYZKsd.css    6.00 kB │ gzip:  1.73 kB
dist/assets/index-CP3d-t8Q.css       41.90 kB │ gzip:  8.99 kB
dist/assets/Messaging-DlvFHw4U.js    19.36 kB │ gzip:  6.47 kB
dist/assets/index-B_ihCNWb.js       271.02 kB │ gzip: 82.63 kB

✓ built in 185ms

```

### frontend-format

```text

> nexawork-frontend@0.1.0 format:check
> prettier --check src tests *.json *.ts index.html

Checking formatting...
All matched files use Prettier code style!

```

### api-diagnostic

```text
2026-10-29 14:09:23,323 | INFO | nexawork.request | POST /api/v1/auth/login -> 200 (0.167s)
2026-10-29 14:09:23,325 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 200 OK"
2026-10-29 14:09:23,460 | INFO | nexawork.request | POST /api/v1/auth/login -> 200 (0.134s)
2026-10-29 14:09:23,461 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 200 OK"
2026-10-29 14:09:23,613 | INFO | nexawork.request | POST /api/v1/auth/login -> 200 (0.151s)
2026-10-29 14:09:23,614 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 200 OK"
2026-10-29 14:09:23,654 | INFO | nexawork.request | GET /api/v1/messaging/conversations/page -> 401 (0.038s)
2026-10-29 14:09:23,655 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/page "HTTP/1.1 401 Unauthorized"
2026-10-29 14:09:23,681 | INFO | nexawork.request | POST /api/v1/messaging/groups -> 201 (0.024s)
2026-10-29 14:09:23,682 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/messaging/groups "HTTP/1.1 201 Created"
2026-10-29 14:09:23,721 | INFO | nexawork.request | POST /api/v1/messaging/conversations/1/attachments -> 201 (0.038s)
2026-10-29 14:09:23,722 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/messaging/conversations/1/attachments "HTTP/1.1 201 Created"
2026-10-29 14:09:23,731 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/attachments/1 -> 404 (0.008s)
2026-10-29 14:09:23,733 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/attachments/1 "HTTP/1.1 404 Not Found"
2026-10-29 14:09:23,760 | INFO | nexawork.request | POST /api/v1/messaging/conversations/1/messages -> 201 (0.026s)
2026-10-29 14:09:23,762 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/messaging/conversations/1/messages "HTTP/1.1 201 Created"
2026-10-29 14:09:23,776 | INFO | nexawork.request | POST /api/v1/messaging/conversations/1/messages -> 201 (0.013s)
2026-10-29 14:09:23,778 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/messaging/conversations/1/messages "HTTP/1.1 201 Created"
2026-10-29 14:09:23,789 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/attachments/1/download -> 200 (0.010s)
2026-10-29 14:09:23,791 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/attachments/1/download "HTTP/1.1 200 OK"
2026-10-29 14:09:23,795 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/attachments/1/download -> 404 (0.004s)
2026-10-29 14:09:23,796 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/attachments/1/download "HTTP/1.1 404 Not Found"
2026-10-29 14:09:23,801 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/messages -> 404 (0.004s)
2026-10-29 14:09:23,802 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/messages "HTTP/1.1 404 Not Found"
2026-10-29 14:09:23,808 | INFO | nexawork.request | DELETE /api/v1/messaging/conversations/1/attachments/1 -> 403 (0.006s)
2026-10-29 14:09:23,810 | INFO | httpx | HTTP Request: DELETE http://testserver/api/v1/messaging/conversations/1/attachments/1 "HTTP/1.1 403 Forbidden"
2026-10-29 14:09:23,821 | INFO | nexawork.request | DELETE /api/v1/messaging/conversations/1/attachments/1 -> 202 (0.010s)
2026-10-29 14:09:23,822 | INFO | httpx | HTTP Request: DELETE http://testserver/api/v1/messaging/conversations/1/attachments/1 "HTTP/1.1 202 Accepted"
2026-10-29 14:09:23,831 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/attachments/1/download -> 410 (0.008s)
2026-10-29 14:09:23,832 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/attachments/1/download "HTTP/1.1 410 Gone"
2026-10-29 14:09:23,844 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/messages -> 200 (0.010s)
2026-10-29 14:09:23,846 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/messages "HTTP/1.1 200 OK"
2026-10-29 14:09:23,867 | INFO | nexawork.request | POST /api/v1/messaging/conversations/1/attachments -> 415 (0.020s)
2026-10-29 14:09:23,869 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/messaging/conversations/1/attachments "HTTP/1.1 415 Unsupported Media Type"
2026-10-29 14:09:23,876 | INFO | nexawork.request | POST /api/v1/messaging/conversations/1/attachments -> 413 (0.006s)
2026-10-29 14:09:23,877 | INFO | httpx | HTTP Request: POST http://testserver/api/v1/messaging/conversations/1/attachments "HTTP/1.1 413 Request Entity Too Large"
2026-10-29 14:09:23,881 | INFO | nexawork.request | GET /api/v1/messaging/conversations/page -> 400 (0.003s)
2026-10-29 14:09:23,882 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/page?cursor=invalid "HTTP/1.1 400 Bad Request"
2026-10-29 14:09:23,889 | INFO | nexawork.request | GET /api/v1/messaging/people -> 200 (0.005s)
2026-10-29 14:09:23,889 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/people "HTTP/1.1 200 OK"
2026-10-29 14:09:23,899 | INFO | nexawork.request | GET /api/v1/messaging/conversations/1/updates -> 200 (0.008s)
2026-10-29 14:09:23,900 | INFO | httpx | HTTP Request: GET http://testserver/api/v1/messaging/conversations/1/updates?after_id=1 "HTTP/1.1 200 OK"
{
  "checks": [
    "real password login contract-0@example.com",
    "real password login contract-1@example.com",
    "real password login contract-2@example.com",
    "anonymous rejected",
    "private metadata/error caching disabled",
    "group creation",
    "bounded upload",
    "validated draft ready",
    "storage key excluded",
    "other member draft hidden",
    "atomic send and binding",
    "message attachment metadata",
    "idempotent retry",
    "authorized binary download",
    "private no-store headers",
    "cross-tenant download denied",
    "cross-tenant messages denied",
    "nonowner delete denied",
    "deletion queued",
    "deleted object immediately hidden",
    "history tombstone",
    "misleading file rejected",
    "oversized file rejected",
    "malformed cursor rejected",
    "directory tenant scoped",
    "bounded updates cursor"
  ],
  "passed": 26,
  "mode": "diagnostic inline ASGI, SQLite FK-enabled, real auth and services; no network/scanner/PG concurrency proof"
}

```
