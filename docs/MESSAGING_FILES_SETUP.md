# Messages and files: setup, API and release notes

## What is implemented

The React workspace adds Messages and Files. Members can find colleagues, create direct/groups, page conversations, read older history, send text and up to ten files with a caption, download private shared files and remove their own files. New-message polling runs every ten seconds only while visible and online; updates are fetched in bounded batches, without overlapping polls. Drafts and retry identifiers are kept in tab memory by conversation, cleared when the messaging workspace/session unmounts. No message text or token is put in localStorage. The UI is lazy-loaded.

The API keeps the existing conversation array response and message history cursor. Conversation listing adds a signed composite cursor and next Link header; `/api/v1/messaging/conversations/page` adds an envelope with member display names. All queries derive organization scope from the authenticated user. No admin override grants access to private conversations.

## Installation and deployment order

1. Use the repository's Python 3.12 and pinned requirements. No application dependencies were added by this change. Run its existing tests/CI, including the new migration and PostgreSQL attachment race test on disposable services. Diagnostic checks in this chat used newer cached packages and do not replace the pinned run.
2. Review and apply new revision `ab921ed70431` through the approved migration process **before** deploying this server. It adds attachment metadata, composite tenant/conversation/message FKs and lifecycle checks; messages gains nullable client request ID/hash plus uniqueness. Existing rows remain intact. Existing audit triggers/identity constraints are untouched. No migration was applied as part of implementation.
3. Start with `ATTACHMENTS_ENABLED=false`; text messages and the UI remain available. An old server lacks the new page/directory APIs: deploy the compatible API before the new client. Keep a coordinated frontend rollback version.
4. For development only, configure a private root, enable attachments and optionally set `ALLOW_UNSCANNED_DEVELOPMENT_FILES=true`. This bypass is explicitly rejected outside development/test and provides no malware guarantee. Do not use real user data in a bypassed environment.
5. For production, provide a persistent private volume outside the web/static root, owned by the non-root API user; set an absolute `STORAGE_LOCAL_ROOT`, `PERSISTENT_LOCAL_STORAGE=true`, `FILE_SCAN_HOST` to a private ClamAV endpoint, and `MESSAGING_RATE_LIMITS_ENABLED=true` with Redis configured. Then enable attachments for a pilot after acceptance. This adapter is for a **single host with persistent storage**, not ephemeral containers or unshared replicas. Provisioning volumes/scanner/Redis is not performed here.
6. Keep ClamAV's signatures updated and its stream-size limit at least the app limit. Its TCP interface has no built-in authentication: isolate it on a private trusted network; never expose it publicly. See [ClamAV documentation](https://docs.clamav.net/manual/Usage/Scanning.html).
7. Schedule `python -m app.workers.attachment_cleanup --run` every 15 minutes with bounded execution and a single operator-owned schedule. It cleans expired drafts and deletion requests in batches of 100, retries store failures, and preserves attached objects and immutable audit history. Run until backlog drains. Monitor cleanup lag, scanner/storage failures, rejected uploads, quota conflicts and disk capacity. Configure ingress body limits and receive deadlines, and a global ASGI concurrency limit appropriate to measured host memory/disk/file-descriptor capacity (a starting pilot cap of 64 requests is proposed, not benchmarked). Per-tenant quotas do not replace global admission control.

No bucket, credentials, cloud service, database privileges, production data or infrastructure were changed. S3/multi-host storage is a separate adapter/deployment milestone, not silently assumed to exist. The streaming protocol isolates application authorization from storage details.

## File policy and lifecycle

Default: TXT/PDF/PNG/JPEG, 10 MiB each, up to ten files per message, nonempty caption, twenty pending drafts per uploader, 1 GiB reserved/accepted bytes per organization over a rolling 24h. Extensions must match inspected content; client MIME is not trusted. Text is checked incrementally for UTF-8/control bytes; media signatures/trailers and ClamAV form layered checks. Signature checks and malware scanning do not establish harmlessness or validate every possible PDF/image structure; files are untrusted downloads and are never rendered inline by this UI. Archives, HTML, SVG and executables are rejected.

An upload reserves metadata/quota before object writing, writes bounded chunks to an exclusive server-generated key, validates/scans, then rechecks authorization before ready. No database transaction remains open during file receipt/scanning. Failure/cancellation deletes bytes when possible and queues the reservation for cleanup. A crash leaves a known expiring key. Ready drafts are private to the uploader and expire after 24h. Atomic message creation locks/claims only ready, unexpired drafts owned by the same user in the same tenant/conversation. A UUID `client_message_id` makes retries of the same body/attachment set return the original message; reusing it for different contents returns 409. Calls without an ID preserve existing semantics.

Current active members may read all attached history in a conversation, including pre-join messages (consistent with existing history). Membership administration is not added here. Future revocation writers must take locks conflicting with the service's authorization locks. In-flight requests/download bytes cannot be recalled. ID-based polling/history is not a commit-ordered lossless event stream; delayed lower-ID commits require a refreshed history view. No websocket/presence/read receipt/edit/delete-message feature is claimed.

Deletion is uploader-only while an active member. It hides downloads immediately, queues physical removal, retains a tombstone/message link and an attributable immutable audit event. Attached content does not expire automatically. Complete retention/legal-hold/account-erasure policy and backup deletion timing remain release decisions. Cleanup is an operational action, not a fabricated end-user audit actor. Preserve both object and metadata backups; restoring only one can leave missing or orphaned content.

## API additions

All require bearer authentication, active organization, server-derived tenant scope; conversation resources also require active membership.

- GET `/api/v1/messaging/people?search=&after_id=0&limit=20`: active same-org names/IDs, no email enumeration. Group maximum remains 100 including creator.
- GET `/api/v1/messaging/conversations/page?limit=30&cursor=...`: `{items,next_cursor}` with members; composite `(created_at,id)` ordering; signed user/org-bound cursor, 400 invalid cursor. Legacy `/conversations` remains an array and exposes a next Link.
- GET `/conversations/{id}/messages?before_id=&limit=50`: unchanged page semantics, additive attachment metadata. GET `/conversations/{id}/updates?after_id=&limit=50`: ascending ID page of newer messages; follow next_cursor as after_id. These paths below share `/api/v1/messaging`.
- POST `/conversations/{id}/messages`: `{body,attachment_ids?:[],client_message_id?:UUID}`; 201 including on replay; nonblank text preserved, ten distinct positive attachment IDs maximum. 409 for expired/claimed files or conflicting retry; invalid claims roll back the entire message.
- GET `/file-policy`: configured availability/limits/extensions. Upload flag is not proof that a scanner/store is healthy.
- POST `/conversations/{id}/attachments`: **raw binary body**, `Content-Type: application/octet-stream`, URL-encoded UTF-8 filename in `X-Filename`. One file per request, no multipart/base64/JSON binary expansion. 201 metadata only after ready; 413 oversized, 415 rejected type/content/scan, 408 receive deadline, 503 unavailable storage/scanner/protection.
- GET `/conversations/{id}/attachments?before_id=&limit=50`: attached/tombstone metadata page, newest ID first. GET `/conversations/{id}/attachments/{aid}`: metadata; drafts visible only to uploader.
- GET `/conversations/{id}/attachments/{aid}/download`: authorized bounded binary stream, attachment disposition, no-store/nosniff; 409 draft, 410 removed for otherwise authorized callers; 404 invisible/missing resources. No public or signed URL is returned.
- DELETE `/conversations/{id}/attachments/{aid}`: 202 deletion/tombstone metadata, idempotent; 403 visible but wrong owner, 404 inaccessible.

401 ends the client session; 403/404 hides inaccessible conversations; 422 typed validation; 429 includes Retry-After; 5xx conceals provider internals. When protection is enabled: 20 conversation creates/min, 60 sends/min, 10 upload attempts/min, 120 downloads/min per organization/user key. The Redis primitive is atomic. These initial limits require workload review; no production benchmark is claimed.

## Rollback and release gates

Disable new uploads/binding first; keep authenticated existing-file downloads and cleanup available. Roll back the application while leaving additive schema/metadata/objects in place; **do not casually downgrade** populated attachment metadata or remove audit protections. Down migration deletes metadata and cannot restore file associations. A coordinated restore needs both database and objects.

Required before release: pinned Python 3.12 API suite, PostgreSQL upgrade/constraint/race checks, actual scanner integration and failure cases, persistent-store/backup/cleanup rehearsal, Redis limits, real browser upload/send/download/session-expiry tests at mobile/desktop widths, accessibility review, and production retention/operator approval. Local build/service checks and the inline ASGI diagnostic are useful evidence, not a production-readiness certification.
