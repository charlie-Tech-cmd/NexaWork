# NexaWork messaging and file sharing: implementation plan

Historical pre-implementation plan; see MESSAGING_FILES_RPI.md and MESSAGING_FILES_SETUP.md for the implemented slice and verification limits.

Review date: 29 October 2026. Scope: read-only repository inspection and planning in response to `Pasted markdown(7).md`.

**Recommendation:** first repair messaging service-test discovery and add a compatible conversation continuation mechanism. Then deliver private, validated attachments through a small storage adapter and a durable upload lifecycle. Keep the modular monolith and existing tenant and audit boundaries.

## 1. Evidence scope and verification

Inspected repository: `charlie-Tech-cmd/NexaWork`, default branch `main`, pinned commit **`5018c8e1a0fbabb6f3abe38c32c5b63692490fad`**, retrieved from GitHub on the review date. All repository links below point to this immutable commit. Findings describe this snapshot, not an assumed deployment. The attachment's stated stack was checked against manifests and code.

The connected GitHub read tools were unavailable. Public GitHub REST metadata and a source archive provided the fallback; all **293 source-tree blobs** were checked against Git blob SHA-1 values in the pinned recursive tree, with no missing or mismatched files after download completed. An older local checkout was located during access troubleshooting; it was not used as current implementation evidence. No repository checkout, branch, code, dependency, migration, database, privileges, bucket, or infrastructure was changed. Only this report and local inspection artifacts were created in the current chat directory.

| Check | Result | Meaning |
| --- | --- | --- |
| Attached requirements retrieved and read | PASS | All ten requested deliverable areas covered below. |
| Pinned source and file integrity | PASS | 293 blobs matched the GitHub tree. |
| Source, schema, migration, test and CI inspection | PASS | Static evidence; links and functions below. |
| Service-test filename/discovery comparison | PASS | Static AST count and comparison with `pytest.ini`, not a pytest execution. |
| Application tests, collection command, load tests | NOT RUN | Planning-only inspection; no test environment created or application code executed. |
| PostgreSQL/Redis/object-storage integration tests | NOT RUN | No database, migration, Redis or object-store operations performed. |
| Production schema, traffic, plans and storage configuration | NOT RUN | Repository evidence cannot establish deployed state. |
| Implementation and deployment | NOT APPLICABLE | Explicitly outside this assignment. |

Method: inventory relevant files, trace routes → dependencies → services → models, compare migrations and tests, inspect CI and configuration, then propose changes. Repository `AGENTS.md` and its `rpi-production-engineering` skill guided research and planning; sensitive cross-tenant file access warrants critical-risk design review when implementation is authorized. This document is a proposal, not approval to implement or provision anything.

## 2. Current-state inventory

| Area | Implemented at this commit | Partial or missing | Evidence |
| --- | --- | --- | --- |
| Direct conversations | Active same-organization users; rejects self; sorted pair; returns existing pair; checks both memberships on reuse; unique-conflict recovery | No membership administration or recovery UI | `create_or_get_direct_conversation`, `_is_direct_pair_unique_violation` [E01] |
| Groups | Name trimming; duplicate/positive IDs; same-org active users; creator is admin; maximum 100 total users including creator; atomic group/member creation | Role exists in data but no add/remove/promote/leave endpoints | `create_group_conversation` [E02], `ConversationMember` [E07] |
| Conversation membership | Unique conversation/user; organization-scoped composite FKs; active membership required for message send/read and listing | `last_read_at` exists without read-receipt operation; no concurrent revocation contract | `_require_active_membership` [E03], [E07] |
| Sending messages | Active sender + active membership; trimmed nonblank body, maximum 10,000 characters in service; commit/rollback | Text only; no idempotency, attachment binding, editing/deletion operation, durable message audit event | `send_message` [E04], `MessageCreate` [E09] |
| Message listing | Tenant/conversation filters; descending ID query, `limit + 1`, chronological page output, older-page cursor | No realtime/delta API; ID order is not guaranteed commit order | `list_messages` [E05] |
| Conversation listing | Active user + membership filter; `(created_at DESC, id DESC)`; limit 50 default, 100 maximum | No continuation parameter, cursor or pagination metadata | `list_conversations` [E06], `get_conversations` [E08] |
| Identity and tenant access | Bearer JWT; active user lookup; token version; active organization; tenant derived from user; generic 404 for inaccessible conversations | Messaging does not use named RBAC permissions; membership is its current authorization rule | `get_current_user`, `get_current_organization` [E10]; `_raise_service_error` [E08] |
| Database integrity | `conversations`, `conversation_members`, `messages`; composite tenant FKs; direct-pair uniqueness; member-role/body checks | Membership activity/count are service invariants, not enforced by FKs; attachment tables absent | [E07], [E11], [E12], messaging migration [E13] |
| Abuse controls | Redis atomic counter primitive; login/onboarding/recovery/reset wrappers; auth dependency failures handled | No messaging-specific limiter in routes/services; no upload limits or quota controls | [E14], [E15], [E08] |
| Storage | `StorageService` protocol with bytes upload, delete, get_url | No implementation, download stream, attachment metadata, scanner, upload route, cleanup worker or storage configuration | [E16], [E17], [E18] |
| Audit | Tenant-scoped actor records; immutable audit rows; protected audited identities; user-service examples | Messaging service does not insert audit records | [E19], [E20], [E21] |
| Frontend | Existing React workspace for other modules | No messaging workflow or attachment client at this snapshot | `frontend/README.md` [E22], inspected `frontend/src/api.ts` and `App.tsx` |
| Verification | API flows, tenant-denial test, opt-in PostgreSQL direct-creation race test; CI provisions PostgreSQL 16 and Redis | 12 service tests have an undiscovered filename; pagination and upload coverage gaps below | [E23], [E24], [E25], [E26], [E27], [E28] |

The product specification contains wider roadmap capabilities. It is not evidence that realtime messaging, uploads, deletion or storage providers already work. No active production credentials or storage resources were assumed or inspected.

## 3. Findings and evidence

### F1 — Confirmed functional defect: conversations beyond the first 100 are unreachable through listing

`app/services/messaging_service.py::list_conversations` accepts only `limit`, sorts by `created_at DESC, id DESC`, and calls `.limit(limit)`. `app/api/routes/messaging.py::get_conversations` accepts only limit and returns a JSON array. Repeating the request cannot advance. With 101 accessible conversations, even `limit=100` never returns the oldest one. This is a direct consequence of the code, not a production incident reproduced here. [E06], [E08]

`tests/api/test_messaging.py::test_messaging_api_enforces_pagination_and_cursor_boundaries` creates three conversations and tests `limit=1` plus invalid limits, but never traverses subsequent conversation pages. It does traverse message pages. [E23]

**Action:** additive continuation preserving list response and current order; regression dataset >100, tied timestamps and multiple tenants. Do not silently replace the array with an envelope or order conversations solely by ID.

### F2 — Confirmed verification defect: messaging service tests excluded from default discovery

`pytest.ini` specifies `python_files = test_*.py`; `tests/services_test_messaging_service.py` does not match. Static AST inspection finds **12 test functions** in that module. CI invokes `python -m pytest -q` without explicitly naming it. Thus these source tests are omitted by normal filename discovery. This is configuration evidence; pytest collection was not run. [E24], [E25], [E28]

They cover direct reuse, inactive membership, cross-org/inactive recipients, groups, active-message access and chronological pagination. API coverage still exists: seven tests in `test_messaging.py`, one tenant-boundary test, and one opt-in PostgreSQL concurrency test. [E31], [E27] Their presence is not a claim they passed this review. Prefer a focused filename rename to `test_messaging_service.py` over globally broadening collection, which could activate unrelated legacy test modules.

### F3 — Confirmed missing control: messaging-specific rate limiting

Messaging routes/services have no limiter calls. Existing wrappers are for authentication-related operations and onboarding; the generic Redis Lua counter is reusable. `app/main.py` registers logging/security middleware, not a messaging limiter. This confirms missing application controls, not measured abuse or an assertion about an external gateway. [E08], [E14], [E15], [E29]

**Action:** add per-user/org controls before exposing uploads; document 429/Retry-After and limiter-outage behavior. Existing `RateLimitUnavailable` handler says authentication is unavailable; use a messaging-appropriate error rather than inheriting misleading text. Do not change auth behavior incidentally.

### F4 — Confirmed feature gap: file sharing is only an abstraction placeholder

`app/integrations/storage/service.py::StorageService` accepts whole-file `bytes` and offers `get_url` without TTL or private-access semantics. No concrete adapter or attachment model/route is in the verified tree. `Settings`, `.env.example` and dependencies have no object-store setup, multipart parser or S3 client. [E16], [E17], [E18], [E32]

**Action:** evolve the seam toward bounded streaming and explicit private retrieval. Do not implement uploads by reading all bytes into memory or using an assumed public URL. New dependencies, if selected, need review and pinning.

### F5 — Potential concurrency risk: authorization check can become stale before commit

`send_message` checks active user and membership, then inserts/commits without locking those authorization rows. Group/direct creation checks active participants before insertion. Composite FKs reject tenant mismatches but do not enforce `is_active`. Concurrent deactivation could occur between check and commit. No membership-removal API exists today; account deactivation is relevant, and future file workflows increase the exposure window. No exploit or failing race test was executed. [E01], [E02], [E03], [E04], [E07], [E12]

**Action:** specify revocation semantics and test PostgreSQL interleavings. For attachment binding/finalization, acquire compatible authorization locks, recheck current user/org/member activity, and ensure revocation writers take conflicting locks. Choose and document lock order; a read/check alone is insufficient. Avoid holding transactions open while receiving/scanning files.

### F6 — Potential ordering risk, not a broken older-history cursor: IDs are allocation order

Current message pagination correctly uses a strict ID boundary and avoids timestamp-tie ambiguity. It does not require the cursor row to exist or belong to the conversation: any positive integer is a boundary inside the separately authorized query. A guessed foreign cursor therefore does not bypass tenant isolation. [E05]

PostgreSQL sequence allocation is not transaction commit order. A delayed lower-ID insert may appear behind a cursor already passed. Current pagination is not a lossless synchronization protocol. Keep history semantics; if realtime or strict complete snapshots are required, design a separate delta/event stream or stronger per-conversation sequence contract. Do not promise snapshot completeness under arbitrary concurrent commits. [S3]

### F7 — Confirmed test limitation: standard SQLite fixture does not explicitly enable foreign keys

`tests/conftest.py::db_session` creates SQLite metadata without a `PRAGMA foreign_keys=ON` listener. Dedicated hierarchy/audit constraint fixtures explicitly enable it. Existing messaging API/service fixtures therefore do not establish composite-FK enforcement. This is a coverage limitation, not evidence PostgreSQL constraints are missing. [E26], [E30]

**Action:** use a dedicated FK-enabled fixture for new attachment/messaging constraint tests; retain PostgreSQL migration/constraint verification. Static SQLite models are not a substitute for Alembic-created PostgreSQL triggers.

### F8 — Confirmed audit gap; policy decision required

Messaging create/send functions commit domain rows without `AuditLog` inserts. User service demonstrates adding audit rows in the same transaction. Audit immutability and actor-scope protections already exist and must remain intact. There is no evidence that every message must currently be audited, so lack of message audit is a policy gap rather than an asserted compliance violation. [E01], [E02], [E04], [E19], [E20], [E21]

**Action:** define sensitive attachment events and audit them without file bodies, signed URLs or sensitive filenames. Keep audit history independent of mutable attachment retention. Cleanup must never remove audit records to permit parent deletion.

### F9 — Optional performance improvements: validate with plans before adding indexes

The conversation index is `(organization_id, created_at)` and omits the ID tie-breaker; membership has `(organization_id, user_id)` and unique `(conversation_id, user_id)`. Message history has `(conversation_id, id)`, appropriate to the observed conversation filter and ID boundary. Models have no mapped relationships that these paths lazy-load; the current pages do not exhibit a demonstrated N+1 pattern. [E07], [E11], [E12]

Conversation joins/sorting may become costly with large membership sets, but no query plans, row counts or latency were obtained. Evaluate `(organization_id, created_at, id)` as a replacement for the existing conversation-order index only if representative PostgreSQL plans justify it. Do not stack overlapping indexes by default. Do not add another message-history index merely to prepend organization ID; global conversation IDs already constrain the indexed range.

### F10 — Confirmed schema/API mismatch at service boundary; optional hardening

`GroupConversationCreate` requires at least one supplied member ID; `create_group_conversation` accepts an empty list and adds only the creator. A payload containing only the creator also permits a one-person group. The upper limit is correctly checked after adding the creator. `MessageCreate` limits raw body length before the service strips whitespace. These are observable code differences, not necessarily product defects. [E02], [E09]

**Action:** explicitly decide whether solo groups are allowed; align service/API invariants if required. Preserve current text validation during the first attachment slice rather than introducing attachment-only messages accidentally.

## 4. Pagination design and compatibility

### Conversation alternatives

| Approach | Benefit | Cost / limitation | Decision |
| --- | --- | --- | --- |
| Keep first page only | No change | Cannot enumerate >100; defect persists | Reject |
| Offset | Familiar API | Inserts/deletes shift pages; deep offsets do work proportional to skipped rows | Reject for primary history |
| ID-only `id < cursor` with ID sorting | Simple keyset | Changes existing created-time order; IDs and timestamps can disagree | Do not use implicitly |
| ID as anchor, resolve its `(created_at,id)` | Compact external cursor; retains order | Extra scoped lookup; removed/inaccessible anchor breaks continuation unless semantics provided | Viable alternative |
| Opaque composite `(created_at,id)` cursor | Matches current total order; no anchor-row dependency | Encoding/version/time precision and validation required | Recommend |

Use the strict predicate:

```sql
WHERE organization_id = :authenticated_org
  AND active_membership_for_current_user
  AND (created_at < :cursor_time
       OR (created_at = :cursor_time AND id < :cursor_id))
ORDER BY created_at DESC, id DESC
LIMIT :limit_plus_one
```

Return first `limit` rows. Next cursor is the last returned tuple only when the extra row exists; terminal pages have no next cursor. Preserve full database timestamp precision; normalize UTC; tie on ID. Cursor payload: `{v:1, created_at:<UTC>, id:<positive>, org_id:<server>, user_id:<server>}`, URL-safe encoded and HMAC authenticated with a dedicated configurable cursor key. Bound input to 1 KiB; verify signature/version/scope; reject malformed/tampered/wrong-scope tokens with 400 and a generic detail. A signed cursor is an integrity convenience, never authorization. Key rotation can invalidate pagination with a documented restart response.

**Compatible first contract:** retain `GET /api/v1/messaging/conversations` JSON array; add optional `cursor` query and a standard `Link: <...cursor=...>; rel="next"` response header. No next link on terminal/empty page. Generate a relative trusted route or a configured trusted API origin; never construct links from unchecked forwarded host headers. Expose `Link` through CORS for browser clients (current configuration does not explicitly expose it). Existing callers get the same body/order/default limit. New clients follow Link; there is no new envelope requirement.

A future `/api/v2/messaging/conversations` could return `{items, next_cursor}` if client needs warrant it. Changing the v1 array into that object would be breaking: introduce a new version, update clients, retain v1 through a documented deprecation window, and measure usage before removal. Do not add v2 merely to fix v1 continuation.

Ordinary new conversations sorting ahead of the cursor do not move older pages or cause duplicates; restart listing to see them. Equal timestamps are handled by ID. Deletes and membership revocation legitimately remove results; self-contained cursors still work. This is a moving dataset, not a transaction snapshot: backdated inserts, delayed commits or changing `created_at` can affect traversal. Keep created time immutable through application APIs; strict historical completeness requires a separate agreed design. Membership is rechecked on each request.

### Message pagination

Preserve existing `before_id`, 50 default/100 maximum, response `{items, next_cursor}`, ID-descending fetch and oldest-to-newest presentation. Positive nonexistent/foreign IDs remain boundaries rather than lookups; invalid zero/negative/types yield 422 at HTTP boundary. `limit + 1` determines whether another older page exists. Newer ordinary inserts do not disturb older-ID traversal. Add equal-timestamp, empty, exact-limit, last-page and concurrent-insert regression cases. Document ID-order and moving-dataset semantics instead of claiming chronological commit order.

## 5. Proposed architecture and responsibilities

Stay inside the existing module layout. Do not introduce a new microservice, message broker or storage provider requirement for text pagination.

```text
Client -- bearer auth --> messaging / attachment routes
                           | existing identity + active organization
                           v
                    messaging / attachment services
                      | authorization + state transitions
                      | short database transactions + audit
                      v
                   PostgreSQL metadata
                      |
             attachment lifecycle rows
                      |
          validation / scanner / cleanup runner
                      |
                StorageService adapter
               /                      \
       private local directory     private S3-compatible bucket
       development/tests           production proposal
```

Proposed files (do not yet exist unless noted):

| Area | Responsibility |
| --- | --- |
| Existing `app/api/routes/messaging.py`, `app/schemas/messaging.py` | Compatible pagination; optional attachment IDs on message creation; response serialization |
| New `app/api/routes/attachments.py`, `app/schemas/attachment.py` | Upload/list/detail/download/delete transport, schemas and safe headers; registered in `app/main.py` |
| Existing `app/services/messaging_service.py` | Membership enforcement; atomic message + attachment claim; preserve text-only behavior |
| New `app/services/attachment_service.py` | Lifecycle, ownership, validation coordination, quotas, authorized retrieval, idempotency and audit |
| New `app/models/attachment.py`, model export in `app/models/__init__.py` | Metadata and tenant-safe constraints |
| Existing `app/integrations/storage/service.py`; new `local.py`, `s3.py`, dependency factory | Bounded stream upload, stream read, delete; private keys only, no authorization delegated to key naming |
| New `app/services/file_validation.py`, scanner adapter | Extension/MIME/content policy, count/size/hash, bounded scan; fake scanner for tests |
| New `app/workers/attachment_cleanup.py` | Reconcile expired uploads and pending deletion; idempotent bounded batches; operator-invoked initially, scheduled only in approved rollout |
| Existing config/example, dependencies, migrations, tests and CI | Explicit setup, reproducibility and isolated verification |

### Storage decision

| Option | Fit | Trade-offs |
| --- | --- | --- |
| Private local directory | Development, temporary-directory tests | Simple; deployment disks may be ephemeral; multiple replicas do not automatically share files; backups and capacity are operator responsibilities |
| Private S3-compatible object store | Recommended production direction | Independent binary storage/streaming; network failures, credentials, lifecycle and cost ownership required; actual provider compatibility must be tested |
| PostgreSQL binaries | Defer | Transactional co-location but adds binary traffic, database/backup size and operational coupling; no requirement justifies it here |

Use one adapter interface with `put_stream(key, stream, max_bytes, detected_type)`, `open_stream(key)`, `delete(key)` and narrowly defined metadata/stat if reconciliation needs it. Return internal metadata, not permanent public URLs. Specify exceptions (unavailable, missing, integrity failure), bounded timeouts and idempotent delete. No SQLAlchemy objects or tenant authorization logic in adapters. Scope interface to the two adapters' actual needs; retain/retire existing protocol methods after checking call sites.

Start with API-mediated upload and download, private objects, a small allowlist and a conservative size limit. This makes validation and revocation simpler; API bandwidth is its scaling trade-off. Add direct-to-store multipart/presigned uploads only after measured bandwidth or file-size needs justify a second protocol, upload completion verification and multipart-abort machinery. Do not conflate a quarantine prefix with a public bucket.

## 6. Minimum additional data model

**Recommend one attachment table, one optional message FK per attachment, and no join table initially.** One message can have many attachments; an attachment can belong to at most one message and cannot be moved to another conversation. Metadata exists before a message; it is a separate resource, not a fake text message. Uploading does not publish it to conversation participants until binding succeeds.

Keep text bodies nonblank for the initial release. Require a caption when sharing files. Attachment-only messages require a deliberate schema/API decision later because `ck_messages_body_not_empty` already exists; a cross-table “body or attachment” invariant cannot be a simple message CHECK. Do not synthesize placeholder text to conceal this decision.

### Proposed `attachments`

| Field | Type / rule | Purpose |
| --- | --- | --- |
| `id` | Integer PK consistent with existing models | Public opaque-to-authorization resource identifier; randomness is not an access control |
| `organization_id`, `conversation_id` | NOT NULL integers, scoped FK | Tenant and conversation ownership, immutable |
| `uploaded_by_user_id` | NOT NULL, tenant-safe FK | Upload owner; only owner may bind drafts initially |
| `message_id` | Nullable integer | NULL while draft; immutable once attached |
| `storage_key` | Bounded string, NOT NULL UNIQUE | Server-generated unpredictable key; never derived from client paths; internal only |
| `original_filename` | Bounded sanitized display string, NOT NULL | Safe download/display name; no raw dangerous path retained |
| `detected_content_type` | Nullable until validation, bounded | Server-detected accepted type; client-declared type is advisory and need not be persisted |
| `size_bytes`, `sha256` | Nullable until received; positive size, 64 hex checksum once validated | Integrity and quota accounting; reject zero-byte uploads initially |
| `status` | Bounded string CHECK | `uploading`, `quarantined`, `ready`, `attached`, `rejected`, `deleting`, `deleted` |
| `created_at`, `updated_at`, `expires_at` | UTC timestamps; expiry for nonattached lifecycle states | Cleanup and observability; updated_at changes on transitions |
| `deleted_at` | Nullable UTC timestamp | Tombstone; metadata remains for message continuity under approved retention |
| `idempotency_key`, `request_fingerprint` | Bounded nullable strings; unique `(organization_id, uploaded_by_user_id, idempotency_key)` | Retry a single upload intent without allocating duplicate metadata; absent keys allow distinct uploads |

Generate a fingerprint from the request's normalized declared metadata and optional client checksum; verify actual checksum on completion. Treat a reused key with different declared data or actual bytes as 409; do not return another file silently. Ready/attached replay returns existing metadata; active uploading/quarantined replay returns its pending resource without a second writer. An expired/rejected/deleted key is a conflict requiring a fresh key, not implicit resurrection. Client checksums do not replace server hashing or validation.

### Constraints and indexes

1. `(conversation_id, organization_id) → conversations(id, organization_id)` and `(uploaded_by_user_id, organization_id) → users(id, organization_id)`. Composite tenant relationships follow existing design.
2. Add unique `(id, conversation_id, organization_id)` on `messages`, enabling nullable composite FK `(message_id, conversation_id, organization_id) → messages(id, conversation_id, organization_id)`. This explicitly prevents binding a same-tenant attachment to a different conversation. PostgreSQL's default nullable-FK behavior permits draft `message_id=NULL`; org/conversation remain NOT NULL and separately constrained.
3. CHECK legal status; `size_bytes IS NULL OR size_bytes > 0`; metadata completeness for ready/attached; `message_id IS NOT NULL` when attached; `message_id IS NULL` for uploading/quarantined/ready/rejected. Deleting/deleted may retain a message link. Service prevents rebind, and direct SQL constraint tests verify cross-scope failures. Database CHECK cannot enforce a maximum attachment count across rows; enforce count in the atomic claim transaction.
4. Restrict deletion of referenced users/conversations/messages initially. Do not cascade objects or audit history. A later whole-conversation deletion workflow must tombstone/clean attachments explicitly.
5. Index `(organization_id, conversation_id, id)` for authorized conversation attachment listing and ID pagination. Index `(message_id, id)` restricted to `message_id IS NOT NULL` for bounded batched message hydration. A full variant may be used for SQLite portability; benchmark/write-overhead review decides, not both.
6. Partial cleanup index `(expires_at, id)` for expirable states, including stale uploading/quarantined/ready/rejected and due deleting rows. Set deletion retry due time in `expires_at`; attached/deleted rows are excluded. A separate worker index should be added only if the chosen worker query cannot use this one.
7. PK, storage-key and idempotency uniqueness already create lookup indexes; do not duplicate them. Message triple uniqueness adds write/storage overhead for integrity rather than a speculative read optimization. No blob index, global hash deduplication, or many-to-many attachment table.

The count of ten attachment IDs includes duplicate detection before querying; every selected row must be ready, owned by the caller, unexpired and in the same org/conversation. Lock IDs in sorted order, create/flush message, bind rows, insert audit events, commit once. Refactor `send_message` transaction ownership so it cannot commit before bindings. Do not call today's committing `send_message` and then claim attachments in a second transaction. Retain direct-pair-specific conflict recovery behavior.

### Lifecycle and failure handling

1. Authenticate and authorize, validate request metadata/limits and limiter/quota, generate storage key, reserve an `uploading` row in a short transaction. Persist before writing bytes so crashes leave a known cleanup target.
2. Receive through a bounded request stream into a private spool/quarantine object. Count actual bytes and hash incrementally. Limit request duration/concurrency and multipart parser overhead, not only the file object after parsing. A dishonest/missing Content-Length cannot bypass counting. Abort storage multipart operations on failure if the adapter uses them.
3. Validate extension/type/content; mark `quarantined` while scanning. No download or bind until ready. For development use a test scanner; production stays fail-closed if the required scanner is unavailable. Store only safe failure codes. Scanner completion is idempotent and must not revive expired/deleting rows.
4. Reauthorize after the long I/O step before finalizing `ready`; commit metadata and upload-complete audit. Removal/deactivation during upload cancels publication and schedules cleanup. Never trust callback identity or client completion claims.
5. Bind through message creation atomically as above; attached files become visible to current active conversation members.
6. Rejected/interrupted/stale ready uploads expire and are cleaned by known storage key. Initial proposed draft TTL: 24 hours. A server-enforced upload deadline bounds active operations below that TTL; workers claim expired rows with locks/conditional state transitions so a still-valid completion cannot race cleanup.
7. DELETE marks `deleting`, denies further retrieval immediately, records deletion request, then deletes bytes outside the transaction. Worker retries until absent; only then mark `deleted` and log completion. Storage 404 is success; storage outage leaves retryable state. Use conditional updates/row locks to serialize binding versus deletion. Retain message FK/tombstone; never claim physical erasure on initial 202.
8. Periodic reconciliation handles object-written/DB-finalization-failed and worker-crash cases. Every generated key has a metadata reservation; adapter-internal multipart leftovers need explicit abort/lifecycle handling. Do not configure automatic expiry on a shared draft/attached prefix that could delete live files.

Authenticated request audits use the actual user and `actor_organization_id`. Background cleanup/scan audits need an approved actor model: existing `AuditLog.user_id` is nonnull. Do not invent a nonexistent actor, rewrite old rows, or relax actor constraints. Prefer a dedicated tenant-scoped system principal per organization, created only through an approved design, or a separately approved extension for system events. This is a production decision gate; until resolved, cleanup may record operational metrics but must not falsely impersonate an end user for completion events. User-initiated delete request audits remain attributable.

## 7. API contract proposal

All paths below use base **`/api/v1/messaging`**. All operations require existing bearer authentication, active user and active organization. Organization and actor IDs come from dependencies, never request fields. Repeat authorization in services. Membership denies return generic 404; a super-admin token does not grant tenant conversation access. No new blanket admin read bypass.

Shared errors: 401 absent/invalid/revoked token; 403 inactive organization; 404 missing or inaccessible conversation/resource; 422 invalid typed request/path/query; 429 quota/rate limit with Retry-After; 503 unavailable required storage/scanner/limiter. Use `{"detail":"..."}` consistent with current API. Hide SQL/provider errors, keys and filenames from error details. Validate new path IDs `>0`. Existing endpoints retain their error behavior unless explicitly documented below.

### 7.1 Existing conversation and message operations

| Method and path | Request and authorization | Success / pagination | Errors and compatibility |
| --- | --- | --- | --- |
| POST `/direct` | `{recipient_user_id: positive int}`; both active same-org users, no self; existing pair requires active memberships | 200 existing `ConversationResponse` for create or reuse | Existing 400 unavailable/self; 409 integrity conflict; unchanged |
| POST `/groups` | `{name:1..255, member_user_ids:[positive IDs]}`; schema requires 1..100 distinct IDs; active same-org participants; creator included within 100 | 201 `ConversationResponse` | Existing 422 schema, 400 service group-limit/user validation, 409 conflict; unchanged |
| GET `/conversations` | `limit=50` in 1..100; proposed optional bounded composite cursor; active memberships only | 200 existing array + optional next Link header; order `(created_at,id)` DESC | 422 limit, proposed 400 cursor; body remains compatible |
| GET `/conversations/{cid}/messages` | Positive `before_id?`, limit 1..100; active member of cid | 200 `{items:[MessageResponse], next_cursor:int|null}`; each page ID ASC, traverses older IDs | Existing 422 boundary and 404 authorization; preserve cursor semantics |
| POST `/conversations/{cid}/messages` | Existing `body:1..10000` nonblank; proposed `attachment_ids:list[positive int]=[]`, max configurable 10, distinct; each ready draft owned by caller/same cid/org | 201 existing message fields plus optional new `attachments:[]` metadata; atomic binding | 422 syntax/count/duplicates; 404 invisible IDs; 409 expired/not-ready/already-claimed; all-or-nothing. Existing text-only calls unchanged |

`ConversationResponse` currently contains `id, organization_id, conversation_type, name, created_by_user_id, created_at`. `MessageResponse` contains `id, conversation_id, sender_id, body, created_at, edited_at`. Do not expose storage data when adding attachment summaries. Batch-fetch attachments for the message IDs in a page rather than per-message lookups; keep returned attachment count bounded by configured maximum.

New response fields are additive but strict external clients can still reject them. Verify known consumers before rollout; if strict compatibility requires it, use `include_attachments=true` opt-in on GET and an explicit response inclusion option for POST, with metadata accessible separately meanwhile. Do not deploy a new client that assumes attachment fields against an old server. Frontend messaging is a separate future slice.

Message create idempotency: propose optional `Idempotency-Key`, max 128 safe characters, scoped by org + sender + conversation. Persist request fingerprint and unique scope, with an additive nullable key/fingerprint on `messages` if enabled. A retry with the same normalized body and ordered attachment IDs returns the same message (200 replay, 201 original); same key/different request returns 409. Without key, preserve existing at-least-once request behavior. This is a separate explicit migration, not an assumed property of attachment claims. Same-key concurrent inserts must roll back/reload only the matching uniqueness conflict; do not mask other integrity errors. Hold no object-store calls in that transaction.

### 7.2 Attachment resource schemas

`AttachmentMetadata = {id:int, conversation_id:int, message_id:int|null, filename:str, content_type:str|null, size_bytes:int|null, status:enum, uploaded_by_user_id:int, created_at:datetime, expires_at:datetime|null, deleted_at:datetime|null}`. For public attached summaries, omit draft expiry/internal failure information. Return nullable size/type only while pending; never expose `storage_key`, bucket, provider credentials, scanner internals or a permanent URL.

| Method and path | Parameters, validation and authorization | Response / pagination | Operation-specific failures |
| --- | --- | --- | --- |
| POST `/conversations/{cid}/attachments` | Multipart exactly one `file`; optional bounded checksum; optional Idempotency-Key; active member; server-selected org/owner/key; proposed size/type policy below | 201 metadata if ready; 202 metadata + relative Location when quarantined/scanning; no pagination | 413 too large, 415 extension/type/content disallowed, 422 missing/multiple parts or checksum mismatch, 409 key conflict; 503 validation infrastructure unavailable. Failed reservation cleaned, no downloadable partial file |
| GET `/conversations/{cid}/attachments/{aid}` | Both IDs positive; active member; scoped org/cid/aid lookup; draft visible only to uploader | 200 metadata, including own pending status; no pagination | 404 other user's draft/invisible ID; deleting/deleted tombstone only for otherwise authorized member |
| GET `/conversations/{cid}/attachments` | Limit 1..100, `before_id>0?`, optional positive `message_id`; current active member; message filter scoped to cid/org | 200 `{items:[metadata], next_cursor:int|null}`; ID DESC with limit+1; attached files and tombstones only | 422 query; 404 inaccessible message filter; no enumeration of others' unpublished drafts |
| GET `/conversations/{cid}/attachments/{aid}/download` | Active member now; scoped lookup; attached and available only; uploader cannot use public endpoint to bypass pending scan | 200 bounded binary stream, Content-Length and safe Content-Type when known; no pagination | 404 invisible, 409 own pending resource, 410 deleted for authorized members, 503 store unavailable; missing attached object is operational failure, not silent success |
| DELETE `/conversations/{cid}/attachments/{aid}` | Active member AND uploader for initial policy; own draft or own attached file; same org/cid; group admin override deferred | 202 metadata status `deleting`; repeat deleting returns 202, deleted returns 204; no pagination | 404 invisible, 403 visible but not owner, 409 illegal transition; no immediate physical-erasure promise |

Download uses `Content-Disposition: attachment` with safe ASCII fallback and RFC 5987-style encoded UTF-8 filename, no CR/LF/control characters; `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`. No inline HTML/SVG execution. Handle client disconnects by closing streams and log delivery outcome separately from authorization/grant audit. Initial endpoint need not implement Range; advertise no range capability until tested, particularly for authorization and resource limits.

A future signed download URL endpoint would return short-lived URL + expiry only after the same authorization check. Proposal: ≤60 seconds TTL, fixed GET/key/disposition, no arbitrary destination, no logging or persistent storage of URL. S3 presigned URLs are reusable bearer capabilities until expiry and cannot enforce a fresh app membership check on every use. This residual revocation window is why API proxy download is the initial recommendation. [S2]

## 8. Security assessment and configurable controls

Assets: message privacy, file contents/metadata, tenant boundaries, storage credentials, immutable audit trail and service capacity. Threat actors include anonymous users, malicious same-tenant members, another tenant, revoked users, a compromised account and a failing provider. Trust boundaries are client/API, service/database, application/storage, scanner and background cleanup.

| Threat | Required control and test | Residual risk / decision |
| --- | --- | --- |
| IDOR or cross-org attachment/message binding | Scoped org/cid/aid queries, active member checks on every operation, owner-only draft binding, composite FKs; swap each ID in negative tests | Key prefixes/unguessable IDs are defense in depth, not permission |
| Forged org/owner/status/key fields | Narrow schemas; reject extra ownership/lifecycle fields for new attachment APIs; assign on server | Existing schemas' extra-field behavior need not be changed globally |
| Revocation during long upload/bind | Reauthorize at finalize and bind; compatible locks/conditional state; no long I/O transaction | Already streamed bytes cannot be recalled; define in-flight download semantics |
| Path traversal or dangerous filename | Server-generated key, normalized bounded display filename, reject NUL/control/path separators, handle Unicode and reserved names; private root containment/no symlink following | Rendering clients must escape display names |
| MIME spoof / polyglot / malware | Small extension allowlist + detected signature/parser validation; mismatch rejects; bounded scanner before ready; fail closed | Signature checks/scanner do not prove content harmless; downloaded files remain untrusted |
| Decompression/resource bomb | No archives initially; no unbounded extraction; bounded parser/scanner CPU, time and memory | Adding office/archive support needs new policy/tests |
| Oversized/slow upload or bulk abuse | Edge/request stream/file limits; bounded multipart parser; per-user/org rate/byte quotas; concurrency slots and timeouts | Controls require measurements and operator tuning |
| Stored script/XSS via preview | Attachment-only delivery; reject HTML/SVG/scripts/executables initially; safe content-disposition and nosniff | Image/PDF parsers can have flaws; no automatic preview/render in first release |
| Public object exposure / stolen URL | Private bucket/root; least-privilege server role, TLS, encryption at rest; no permanent URLs or credentials in client | Operators/provider still have access; no end-to-end encryption claim |
| Duplicate send or competing claim/delete | Unique scoped idempotency, sorted row locks, transactional claim and audit, worker conditional transitions | Retries without idempotency may create duplicate text messages |
| Audit tampering or data leakage | Existing immutable audit and actor constraints preserved; minimal IDs/action/size/result; no bodies/URLs | Retention of immutable actor records must be reconciled with product policy |
| Storage outage / partial success | Persisted state before object write, retryable deletion, reconciliation, safe 503, scanner quarantine | Physical cleanup is eventual, monitored and bounded by agreed SLA |

Recommended **initial configurable proposals**, not measured capacity or existing settings:

- `ATTACHMENTS_ENABLED=false` until rollout; `STORAGE_BACKEND=local|s3`; local permitted only in development/test unless an explicit persistent deployment is approved.
- `ATTACHMENT_MAX_BYTES=10485760` (10 MiB); `ATTACHMENT_MAX_PER_MESSAGE=10`; zero bytes rejected; one file per upload request. Request cap includes bounded multipart overhead (e.g. file max + 256 KiB); enforce at ingress and application receive boundary.
- Allow `.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt` initially. Verify PDF/image formats with bounded parsers; validate text encoding/content with a documented policy. No archives, SVG, HTML, scripts or office formats until reviewed. Extension and detected content must agree; declared MIME is never authoritative. See [S1] for the defense-in-depth rationale.
- `ATTACHMENT_DRAFT_TTL_SECONDS=86400`; upload receive deadline initially 120 seconds; scanner deadline/retry budget explicit; initial cleanup batch 100 and interval 15 minutes once a runner is approved.
- Proposed per-user rates: sends 60/min, upload attempts 10/min, create conversations 20/min; proposed per-org upload attempts 100/min and byte budget 1 GiB/day. At most 2 concurrent uploads/user and a bounded per-process/global admission limit selected from deployment capacity. Treat these as starting settings for review and load tests, not sufficient anti-abuse guarantees.
- Reuse Redis atomic limit primitive for request windows; byte reservations and concurrency leases need atomic reserve/release/expiry rather than plain INCR alone. Charge actual accepted bytes; release unused reservations on failure/timeout. Fail closed with 503 for new writes when limiter/quota protection is required but unavailable; pagination/read behavior can remain available under a separately documented policy.
- Store endpoint, region, bucket and credential source server-side only. Prefer workload credentials over embedded keys if selected provider supports them. Encryption, geographic region, backup policy and retention need owner approval. No credentials are provisioned by this plan.

## 9. Performance, query design and observability

No production performance defect is established. The following are risks and measurable verification proposals.

| Path | Current or proposed complexity | Verification / trigger for change |
| --- | --- | --- |
| Message history | Current bounded ID range and `limit+1`, supported by `(conversation_id,id)` | Synthetic PostgreSQL histories at 10k/100k/1m messages; first/deep page plans; no offset scan; compare rows examined and p95 |
| Conversation history | Membership join + created-time ordering; candidate keyset uses existing indexes initially | 10/100/1k/10k memberships/user with many inaccessible conversations; examine sort and join plans before replacing index |
| Message attachment hydration | One bounded query over page message IDs, then group in memory | Query count remains constant from 1 to 100 messages; no per-message lazy queries; max 1,000 attachment summaries/page at proposed limit |
| Upload/download | Bounded chunks/spool; bytes stored outside DB; API proxy uses network capacity | Concurrent max-size files, slow readers/writers/disconnects; RSS must not grow by full file size per active request; bound disk spool usage too |
| Binding | At most 10 locked attachment rows; short message/audit transaction | Concurrent overlapping claims and delete/finalize; deterministic lock order; lock wait/deadlock metrics |
| Cleanup | Expiry-indexed bounded batches; conditional claims/leases, safe retries | Thousands of stale drafts, partial store outage, worker restart; no live attachment deleted |

Proposed baseline protocol: disposable PostgreSQL 16 to match CI, synthetic data only, record CPU/memory, dataset, concurrency, cache state and EXPLAIN ANALYZE/BUFFERS. Analyze statements on the disposable dataset only. A preliminary target for list endpoints is p95 <250 ms at 20 concurrent readers with 100-row pages on an agreed staging-size machine; this is a proposed acceptance budget needing owner confirmation, not an observed number. Upload/download throughput and scan latency budgets depend on provider/network; record them before setting release SLOs.

Observe endpoint latency/error/429 counts, bytes uploaded/downloaded, validation/scanner rejection rates, storage latency/errors, quarantine age, oldest cleanup due age, deletion retries and quota reservation leaks. Use resource IDs and request correlation; never log bearer tokens, signed query strings, file content or full sensitive filenames. Alert on actionable backlog age, missing attached objects, repeated cross-scope attempts and storage saturation. Audit access-granted events are not proof a client received every byte.

## 10. Focused testing matrix

These are future tests, not results from this inspection. Prefer testing public behavior and invariants, not internal implementation shape. Preserve existing messaging/security tests and immutable audit guarantees.

| Scenario / acceptance | Layer | Infrastructure |
| --- | --- | --- |
| Fix service module discovery; explicitly collect all 12 existing tests; record collected/executed/skipped counts | Collection + service regression | Existing Python test environment; ordinary SQLite fixture for service behavior |
| Direct reuse, self/cross-org/inactive target, inactive existing membership, complete pair after conflict | Service + API + existing race | SQLite for deterministic behavior; PostgreSQL for race |
| >100 conversations fully traversable; limits 1/50/100; 0/101 reject; no duplicates/omissions in fixed dataset | Service + API | SQLite |
| Equal created_at tuples; IDs with timestamp order deliberately different; anchor removed; empty/exact/full terminal pages | Service + API | SQLite; PostgreSQL timezone/precision checks |
| Cursor malformed, oversize, wrong version/signature/user/org; old array response unchanged; browser can read Link | Contract + API | SQLite; browser smoke later for CORS exposure |
| Message cursor positive nonexistent/foreign boundary; ties in timestamps; ordinary inserts while paging | Service + API | SQLite; PostgreSQL separate-session interleavings |
| No token, invalid token/version, inactive user/org, super-admin tenant denial on every new endpoint | API | Existing auth fixtures, synthetic records |
| Swap org/cid/aid/message/uploader IDs on upload, list, status, bind, download, delete | Service + API + DB constraints | SQLite behavior; FK-enabled SQLite and migrated PostgreSQL for integrity |
| Valid upload, metadata retrieval, caption + multiple files, text-only old request | Unit + API | Temp-directory adapter and fake scanner; no cloud |
| Size exactly max/max+1, empty, chunked/lying Content-Length, multiple parts, parser overhead and slow/disconnect | API + request streaming integration | Local app/test server with bounded fake storage; ingress tests in staging |
| Misleading extension, double extension, MIME mismatch, invalid image/PDF, binary text, Unicode/path/control filename | Validation unit + API | Synthetic bytes; no real user files |
| Malware result/scan timeout/unavailable; no pending download or binding | Service + scanner contract | Fake scanner; dedicated test scanner service for integration |
| Attach >10, duplicate ID, expired, wrong owner, same-org wrong conversation, already claimed | Service + API + DB | SQLite and migrated PostgreSQL constraints |
| Message+bindings+audit atomic; any invalid attachment or audit failure rolls all back | Service + integration | SQLite for rollback; PostgreSQL for actual constraints/triggers |
| Same attachment claimed by two sends; bind vs delete; finalize vs cleanup; user/member/org revocation during upload | Concurrency integration | Disposable PostgreSQL, independent sessions and synchronization barriers |
| Same upload/message idempotency key concurrent/replayed/different payload; unrelated IntegrityError not swallowed | API + concurrency | SQLite replay; PostgreSQL conflict behavior |
| Adapter write/read timeout, partial write, missing object, delete failure, final DB failure after object write | Fault-injection service tests | Fake adapter plus temp storage |
| Cleanup expired drafts/rejected files; no attached files removed; crash after deletion; audit immutability survives | Worker + integration | Temp storage; PostgreSQL for claims/locks and audit triggers |
| Private bucket, denied anonymous access, streaming integrity/hash, repeated delete, provider headers | Storage contract | Disposable local S3-compatible test service and isolated provider sandbox if selected |
| Rate exceed, byte reservations, concurrency leases, Redis outage | Unit/API + integration | Mock for logic; local Redis for atomic behavior |
| New migration fresh/upgrade/repeat, constraint rejects, old text app on expanded schema; retained audit invariants | Migration integration | Disposable PostgreSQL 16, never production/Supabase |
| Constant query count, large histories, max concurrent file memory/disk bounds | Performance/resilience | Synthetic PostgreSQL + local/test object store; record environment |

The existing default SQLite fixture uses a shared StaticPool/session and is inappropriate evidence for real concurrent transactions. Use separate PostgreSQL sessions for races. Reuse safety gates in `test_messaging_postgres_concurrency.py`: local host, database `nexawork_migration_test`, user `nexawork_test`, explicit opt-in `NEXAWORK_TEST_POSTGRES_CONCURRENCY=1`. Add similarly explicit protection for any object-store sandbox. A fixture must never fall back to live credentials. Do not use a live production or Supabase database or real user data.

When implementation is authorized: run focused pytest collection/tests first, then existing full suite and the security workflow's migration checks in disposable services; record skipped integration tests distinctly. Existing CI starts from revision `3f7330e74933`, upgrades to head twice and checks a single head. Extend with attachment-specific schema/behavior assertions; merely succeeding at `upgrade head` does not prove every new constraint. [E28]

## 11. Migrations, configuration and deployment proposal

No migration or infrastructure change was applied. Current migration graph statically ends at `e7b42c9d1a60`; verify the live repository head again before creating any future revision. Messaging tables were introduced in `8582f542826e`, followed by audit-scope/identity/immutability revisions. Do not edit historical revisions. [E13], [E20]

| Proposed change | Why / database impact | Compatibility and data preservation | Local verification and rollback |
| --- | --- | --- | --- |
| M0: pagination/test-discovery repair | No schema change; optional cursor key/config and CORS expose Link | Existing conversation body/order preserved | Unit/API/contract tests; revert application changes, no data rollback |
| M1: attachment metadata | New attachments table, tenant FKs/CHECKs/uniques/query indexes; messages triple unique | Additive; existing messages untouched; attachment feature disabled | Fresh + prior-head upgrade on disposable PG, invalid-row tests; app rollback leaves new rows/table. Dropping table after usage loses metadata and is not routine rollback |
| M2: optional message idempotency | Nullable scoped idempotency key/fingerprint and unique scope on messages | Existing rows remain NULL; no backfill of fictitious keys | Replay/race tests; old app still creates rows; app rollback preserves columns; do not drop populated columns casually |
| Conditional order index | Replace `(org,created_at)` with `(org,created_at,id)` only after evidence | No row semantics changed; plan locking and online build based on actual volume | Compare plans on synthetic PG; verify new index before old removal; index rollback retains data |
| Storage/scanner/runner setup | Private store/root, credentials, validation/scanner process, expiry runner | No assumed existing resources; not deployed with metadata alone | Isolated contract/fault tests; disable upload flag, continue authorized existing downloads/cleanup; retain stored objects |
| Background audit actor design | Only if required for attributable worker completion | Separate approved identity/audit design; no weakening of current immutability/actor rules | Existing and new audit identity tests; rollback must preserve audit history |

New configuration proposal: `ATTACHMENTS_ENABLED`, `STORAGE_BACKEND`, `STORAGE_LOCAL_ROOT`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET`, workload credential configuration (or server-only access key/secret if unavoidable), size/count/allowlist/TTL/deadline settings, scanner endpoint/timeout and rate/quota settings, `PAGINATION_CURSOR_SECRET`. Names are proposed, not existing env vars. Add validated settings and nonsecret `.env.example` entries at implementation time. Production must reject insecure local storage or missing required scanner/store configuration when uploads are enabled. Optional disabled attachments must not prevent existing text messaging startup.

Dependencies: a pinned multipart parser for FastAPI multipart uploads (not in current manifest), a pinned S3 SDK only if S3 adapter chosen, and a bounded file-type/parser/scanner integration appropriate to the approved allowlist. Explain licensing, maintenance, audit results, container/native-library requirements and failure behavior before adding them. Existing Redis/SQLAlchemy/FastAPI are reused. No new queue framework is required for initial indexed polling; select a runner owner and scheduling mechanism before production. Avoid installing provider-specific dependencies in the pagination milestone.

Proposed deployment sequence:

1. Review pagination contract, file policy, storage/scanner ownership, quota and retention/audit decisions. Recheck current source head and inspect production-scale table sizes through a separately authorized process.
2. Run tests against disposable PostgreSQL/Redis/local S3, never a live DB. Rehearse fresh and populated upgrades; check old app compatibility and immutable audit invariants.
3. Provision an isolated private nonproduction store/scanner, root/bucket permissions, TLS/encryption, capacity/quotas and observability after authorization. No public read policy. If API-proxied, browser-to-bucket CORS is unnecessary.
4. Apply additive migrations via approved deployment process with lock/statement timeouts appropriate to measured size. Build large existing-table uniqueness/indexes with an explicitly reviewed lock strategy; no assumption an online build is necessary for tiny tables.
5. Deploy backward-compatible server with uploads disabled; validate text regression, pagination and readiness. Then enable a limited tenant pilot, with cleanup/scanner running before file creation is enabled.
6. Verify upload → scan → bind → metadata → authorized download → delete/cleanup; test cross-org denial and revocation. Expand only after error/backlog/resource measurements meet agreed budgets.

Rollback/stop criteria: disable new uploads/binding on any cross-tenant exposure, unchecked-file retrieval, failed integrity/audit invariants, or unbounded cleanup/scan backlog. Keep existing text messaging available if unaffected. Revert application version only if it tolerates expanded schema; leave metadata/objects intact. Continue safe authorized retrieval and cleanup through a compatible version. Do not automatically drop tables, bucket contents, audit triggers or history. Coordinate object backups and metadata recovery: DB-only restores can reference missing objects, object-only restores can revive orphaned content. Provider backups/version retention and purge delays need explicit policy; no instant total-erasure claim.

## 12. Roadmap with independently reviewable acceptance criteria

| Milestone | Scope / likely touchpoints | Acceptance and review gate |
| --- | --- | --- |
| **0 — Collect the existing service tests** | Rename only `tests/services_test_messaging_service.py` to matching `test_*.py` name; preserve assertions | Default collection includes all 12 existing service tests; record pass/fail/skip honestly; fix any real failure in a separately reviewed focused change. No API/schema/infrastructure change |
| **1 — Complete conversation traversal** | Messaging list service/route/schema helpers, cursor config, CORS response exposure, API/service tests | >100 accessible conversations traversed without omission/duplicate on fixed dataset; ties, invalid/scope cursors, insert/delete semantics covered; old array/order unchanged; header readable by browser; no migration |
| **2 — Local attachment vertical slice** | One table/migration, local adapter, validation/scanner seam, upload/status, atomic message binding, metadata/download, cleanup and audit design | Approved size/type/count policy enforced; private scan-before-ready; cross-org/cid/owner denials; rollback atomicity; failure cleanup; text-only requests preserved. Runs only in dev/test until production gates below |
| **3 — Lifecycle and concurrency hardening** | Idempotency if approved; delete worker/reconciliation, revocation locking, quotas/Redis, PostgreSQL races | One winning claim, safe duplicate retries, revoke/bind/delete/cleanup races pass; no orphan leakage; attributable audit behavior; backlogs visible |
| **4 — Production storage readiness** | S3 adapter, test service/sandbox, scanner deployment, config/runbook and backups | Private-access contract verified; provider failures and cleanup exercised; operating owner, data region/retention/restore agreed; bounded memory and measured budgets; no live data in tests |
| **5 — Pilot and client integration** | Separate messaging UI/API client slice, loading/pending/retry/tombstone states, staged feature enable | End-to-end authorized workflow and cross-org denial; no downloaded content preview without policy; client compatibility and pilot metrics reviewed before expansion |

Milestone 2 is a reviewable local feature slice, not authorization to release unscanned files. A fake scanner is test-only. Avoid one enormous PR containing all milestones. After each, review evidence, invariants and remaining questions before implementing the next.

## 13. Risks, assumptions and decisions for review

| Decision | Recommendation | Who / when to resolve |
| --- | --- | --- |
| Pagination compatibility | v1 array + optional composite cursor + next Link; v2 envelope only if needed | API owner before milestone 1 |
| File-only messages | Require caption initially; design explicit alternate body invariant later | Product/API owner before changing message schema semantics |
| File types, size and quotas | Narrow allowlist, 10 MiB, ten/message; proposed request/byte limits subject to usage | Product/security/operations before milestone 2 |
| Storage provider, region, budget | Provider-neutral seam; local test, private S3-compatible production | Operations/data owner before milestone 4; no assumption of existing bucket |
| Scanner and background audit identity | Fail closed for production scan; approve worker actor model without weakening audit constraints | Security/maintainer before production lifecycle completion |
| Deletion powers | Uploader + active membership initially; moderator/admin override separately approved | Product/security before delete API |
| Retention/legal hold/backups | Draft expiry 24h proposed; no automatic purge of attached content until policy approved | Data owner before production; jurisdiction obligations not determined here |
| Member removal/history/rejoin | Current active members can read existing history; no special pre-join filter today | Product/security before membership management; files should follow agreed history policy |
| Revocation and download | Recheck on each request/finalize/bind; proxy first; in-flight delivery cannot be recalled | Security before production; signed URL exposure window requires explicit acceptance |
| Capacity/SLO/ownership | Measure synthetic/staging workload; assign cleanup/scanner/storage owner and alerts | Operations before pilot |

Assumptions are deliberately reversible: one attachment belongs to one message, uploaded drafts are private to their uploader, existing nonblank text contract stays, storage is private, and no end-to-end encryption/realtime system is part of this slice. If any assumption fails product review, revisit the relevant API/model before implementation.

## 14. Recommended first milestone

**Milestone 0: repair discovery of the 12 existing messaging service tests.** It is the smallest valuable, testable change: one focused test-file rename, explicit collection evidence and execution using an isolated nonproduction fixture. It strengthens the baseline before changing a tenant-sensitive service, with no contract, schema or infrastructure impact. Do not count a newly collected failure as success or weaken assertions to pass.

The first user-visible milestone is then conversation continuation (milestone 1). Accept it only when a synthetic user can traverse 101+ accessible conversations while inaccessible and inactive memberships remain hidden, duplicate timestamps are stable, malformed cursors fail safely, and legacy clients still receive the same array format. File sharing follows as a separate reviewed feature.

## Appendix A — Repository evidence links

Links below are pinned to the inspected commit; function names and line anchors identify supporting source. Test links prove test definitions and assertions, not executed outcomes.

| Ref | File / function | Supporting evidence |
| --- | --- | --- |
| [E01] | `app/services/messaging_service.py` — `create_or_get_direct_conversation` (line 73) | Direct pair creation, membership verification and specific uniqueness recovery |
| [E02] | `app/services/messaging_service.py` — `create_group_conversation` (line 175) | Group validation and atomic creation |
| [E03] | `app/services/messaging_service.py` — `_require_active_membership` (line 54) | Active tenant-scoped membership lookup |
| [E04] | `app/services/messaging_service.py` — `send_message` (line 275) | Text validation, authorization and committing service |
| [E05] | `app/services/messaging_service.py` — `list_messages` (line 311) | ID-keyset message paging and chronological page presentation |
| [E06] | `app/services/messaging_service.py` — `list_conversations` (line 245) | Created-time ordering and bounded listing without continuation |
| [E07] | `app/models/conversation_member.py` — `ConversationMember` (line 17) | Membership role, uniqueness, composite FKs and indexes |
| [E08] | `app/api/routes/messaging.py` (line 1) | Routes, status translation, list contract and authorization dependencies |
| [E09] | `app/schemas/messaging.py` (line 1) | Existing request/response shapes and validation |
| [E10] | `app/api/dependencies.py` — `get_current_user` (line 38) | JWT, token-version, active user and organization enforcement; get_current_organization is in the same file |
| [E11] | `app/models/conversation.py` — `Conversation` (line 18) | Direct/group checks, composite FKs, uniqueness and ordering index |
| [E12] | `app/models/message.py` — `Message` (line 16) | Text constraint, tenant FKs and history/sender indexes |
| [E13] | `migrations/versions/8582f542826e_create_messaging_tables.py` — `upgrade` (line 21) | Messaging DDL; downgrade reverses tables and user composite uniqueness |
| [E14] | `app/core/rate_limit.py` (line 1) | Existing authentication/onboarding rate-limit wrappers |
| [E15] | `app/core/redis.py` — `check_rate_limit` (line 36) | Atomic Lua-backed rate-limit primitive |
| [E16] | `app/integrations/storage/service.py` — `StorageService` (line 4) | Bytes-based upload/delete/get_url protocol only |
| [E17] | `app/core/config.py` — `Settings` (line 9) | Existing configuration and production validation |
| [E18] | `requirements.txt` (line 1) | Pinned runtime stack and absence of multipart/S3 packages |
| [E19] | `app/models/audit_log.py` — `AuditLog` (line 18) | Actor-scoped audit metadata and SQLite immutability triggers |
| [E20] | `migrations/versions/e7b42c9d1a60_make_audit_logs_immutable.py` — `upgrade` (line 18) | PostgreSQL audit mutation prevention |
| [E21] | `app/services/user_service.py` (line 1) | Existing transactionally inserted audit events |
| [E22] | `frontend/README.md` (line 1) | Frontend scope explicitly excludes messaging |
| [E23] | `tests/api/test_messaging.py` (line 1) | Seven API tests including boundaries and message page traversal |
| [E24] | `pytest.ini` (line 1) | test_*.py default discovery pattern |
| [E25] | `tests/services_test_messaging_service.py` (line 1) | Twelve messaging service tests with nonmatching module filename |
| [E26] | `tests/conftest.py` — `db_session` (line 24) | SQLite StaticPool fixture, no explicit FK PRAGMA |
| [E27] | `tests/integration/test_messaging_postgres_concurrency.py` — `test_concurrent_direct_creation_recovers_from_unique_conflict` (line 25) | Opt-in local PostgreSQL synchronized direct-pair race and safety stops |
| [E28] | `.github/workflows/security.yml` (line 1) | Disposable PostgreSQL 16, Redis, migration upgrades, opt-in concurrency and default pytest invocation |
| [E29] | `app/main.py` (line 1) | Router/middleware registration, CORS and RateLimitUnavailable response |
| [E30] | `tests/security/test_audit_log_tenant_constraints.py` (line 1) | Explicit FK-enabled SQLite fixture and audit immutability tests |
| [E31] | `tests/api/test_messaging_tenant_boundary.py` — `test_other_organization_cannot_read_or_send_conversation_messages` (line 34) | Cross-tenant message read/send denial |
| [E32] | `.env.example` (line 1) | Existing nonsecret configuration template with no storage settings |
| [E33] | `app/db/session.py` (line 1) | Session settings, request close and service-owned commits |
| [E34] | `AGENTS.md` (line 1) | Repository investigation and evidence guidance |
| [E35] | `.agents/skills/rpi-production-engineering/SKILL.md` (line 1) | Research and plan workflow applied |

[E01]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/messaging_service.py#L73
[E02]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/messaging_service.py#L175
[E03]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/messaging_service.py#L54
[E04]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/messaging_service.py#L275
[E05]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/messaging_service.py#L311
[E06]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/messaging_service.py#L245
[E07]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/models/conversation_member.py#L17
[E08]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/api/routes/messaging.py#L1
[E09]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/schemas/messaging.py#L1
[E10]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/api/dependencies.py#L38
[E11]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/models/conversation.py#L18
[E12]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/models/message.py#L16
[E13]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/migrations/versions/8582f542826e_create_messaging_tables.py#L21
[E14]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/core/rate_limit.py#L1
[E15]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/core/redis.py#L36
[E16]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/integrations/storage/service.py#L4
[E17]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/core/config.py#L9
[E18]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/requirements.txt#L1
[E19]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/models/audit_log.py#L18
[E20]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/migrations/versions/e7b42c9d1a60_make_audit_logs_immutable.py#L18
[E21]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/services/user_service.py#L1
[E22]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/frontend/README.md#L1
[E23]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/tests/api/test_messaging.py#L1
[E24]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/pytest.ini#L1
[E25]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/tests/services_test_messaging_service.py#L1
[E26]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/tests/conftest.py#L24
[E27]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/tests/integration/test_messaging_postgres_concurrency.py#L25
[E28]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/.github/workflows/security.yml#L1
[E29]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/main.py#L1
[E30]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/tests/security/test_audit_log_tenant_constraints.py#L1
[E31]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/tests/api/test_messaging_tenant_boundary.py#L34
[E32]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/.env.example#L1
[E33]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/app/db/session.py#L1
[E34]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/AGENTS.md#L1
[E35]: https://github.com/charlie-Tech-cmd/NexaWork/blob/5018c8e1a0fbabb6f3abe38c32c5b63692490fad/.agents/skills/rpi-production-engineering/SKILL.md#L1

## Appendix B — Primary design references

Retrieved 29 October 2026. These support general design choices, not claims about NexaWork deployment.

- [S1 — OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html): layered upload validation, safe naming, private storage and resource controls. This plan selects concrete controls rather than claiming any check alone proves safety.
- [S2 — Amazon S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html): time-limited capabilities can be reused until expiry; practical authorization/revocation trade-off for future direct retrieval.
- [S3 — PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html): sequences are not rolled back like transactional data; statement snapshots and sequence allocation do not imply commit-ordered pagination. Production version is unverified; CI uses PostgreSQL 16, whose semantics must be tested in the planned environment.

No compliance certification, production benchmark, test pass, deployment state or infrastructure availability is asserted by this plan.

[S1]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
[S2]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
[S3]: https://www.postgresql.org/docs/current/transaction-iso.html
