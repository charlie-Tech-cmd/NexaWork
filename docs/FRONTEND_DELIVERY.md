# Workspace frontend delivery — 2026-10-27

Status: PARTIAL VERIFICATION / NOT RELEASE READY. Local frontend implementation is complete for the scoped first workspace. No deployment or merge was attempted.

## Research and design

Baseline: main `a39b177`, clean checkout before work. Inspected API routes, schemas, service filtering, repository policy and product specification. The backend exposes identity, organization onboarding, parent-scoped hierarchy, active users, roles and permissions. It does not expose main-branch messaging or product/order tracking. PR #2 remains separate.

Audience: organization members and administrators carrying out everyday workspace administration. Design: calm, clear, structured; system typography, forest-green navigation, warm neutral surfaces, restrained green actions, explicit states and a hierarchical organization explorer. Alternative directions considered: dense operations console (more information but unnecessary before reporting APIs exist) and employee social hub (depends on unmerged messaging). Selected the workspace directory direction because it matches main today.

Architecture: browser React UI → same-origin /api/v1 proxy → existing FastAPI authorization/services → existing storage. Backend code and data contracts are unchanged. Vite is smaller than a server-rendered framework for this authenticated client and keeps the existing FastAPI server authoritative. React is consistent with the product specification. Exact dependencies and transitive dependencies are locked. System fonts and CSS-only diagrams require no external asset licensing or requests.

Security boundaries: token remains in memory; backend alone authorizes requests and tenant IDs. No client-computed role grants. No token parsing or persistent browser storage. UI validation is convenience, not security enforcement. No HTML injection, automatic mutation retries, telemetry, production data, destructive controls or secrets. Known backend audit issues remain unresolved.

## Acceptance and evidence

| Requirement | Verification | Result |
| --- | --- | --- |
| Strict type checking and optimized build | `npm run build`, TypeScript 7.0.2 / Vite 8.3.5 | PASS |
| Consistent formatting | `npm run format:check` | PASS |
| API failures, authorization headers, validation errors, malformed responses, no cookie use, hierarchy routes and team payload | `npm test`, 10 tests | PASS |
| Dependency audit | `npm audit --audit-level=high` | PASS: 0 reported vulnerabilities |
| Sign-in and real response rendering | Browser with isolated fixture API; organization shown as “Test workspace · QA only” | PASS for fixture integration |
| Edit user profile and refresh directory | Browser: Test Member → Updated Test Member; server-confirmed success | PASS for fixture integration |
| Region → branch → department → team | Browser drill-down and team creation, success “Team created.” | PASS for fixture integration |
| Stale parent records and duplicate hierarchy IDs | Browser exposed issues; fixed synchronous resource-key gating and level-qualified breadcrumb keys; retested | PASS |
| Permission and session failure handling | Browser fixture 403 stays signed in with permission error; 401 returns to sign-in with session-ended notice | PASS |
| Network failure form recovery | Fixture stopped during team create; entered values retained and error displayed | PASS |
| Role permission details | Browser loads role and USER_VIEW permission | PASS for fixture integration |
| Mobile layout | Overview and menu at 390×844; roles at 320×720; document scrollWidth == clientWidth (305px excluding scrollbar) | PASS for checked screens |
| Accessibility | Semantic controls, labels, table caption, focus-to-main navigation, visible focus styles and browser accessibility-tree inspection | PARTIAL: no full screen-reader, keyboard-only or automated WCAG audit |
| Full backend/database integration | Local Python installation previously blocked by unavailable greenlet==3.5.6; PostgreSQL/Redis-backed frontend flows not exercised | NOT RUN |
| Onboarding/recovery delivery, people creation, role creation, settings mutation | Implemented against inspected route/schema contracts; not browser-exercised with the real backend | NOT RUN end-to-end |
| Multi-browser and measured performance | Build output inspected (~247 kB JS / 76 kB gzip, ~17 kB CSS / 4.6 kB gzip); no runtime performance claims | NOT RUN |
| Hosted CI | Workflow added; no remote branch push in this task | NOT RUN |

Browser QA used a separate loopback fixture API and preview, outside the application package. Fixture records are not shipped in the frontend. Screenshots in the task outputs show sample data, not a connected production organization.

## Remaining scope and release gates

This first workspace covers onboarding/sign-in, people create/edit/list, hierarchy create/list, role create/list/permission inspection, and organization settings. Employee-record administration, hierarchy editing, role assignment, account deactivation, super-admin operations, and messaging remain future work. There are no dummy feature buttons for those capabilities.

Before release: exercise these flows against a disposable real backend/database, address applicable backend audit findings, configure real email recovery, complete accessibility/browser acceptance and deploy-time HTTPS/proxy/security headers. No current-user capability endpoint exists; denied actions therefore show explicit errors rather than a guessed permission model. Missing employee permissions from onboarding and broken aggregate dashboard are backend limitations, not fabricated frontend success.

Rollback: remove/revert this independent frontend package and hosting bundle. No database migration is required. Hosting rollback was not executed because nothing was deployed.
