# NexaWork workspace frontend

React + TypeScript + Vite client for the existing FastAPI backend. The messaging/files slice extends main at `f808143`; deploy its matching API and additive migration before this client. No sample records or mock API are included in the application.

## Run locally

Use Node 24 (or Node >=22.12). Start PostgreSQL, Redis and FastAPI using the root repository instructions. From the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:3000. The development server forwards `/api` requests to `http://127.0.0.1:8000`. To use a different local backend, copy `.env.example` to `.env.local` and set `API_PROXY_TARGET`. This is a server-side development setting, not a browser secret.

Sign in as a member, organization administrator, or with an employee ID. New organizations can use **Create a workspace**, then sign in through **Administrator**. Refreshing the page intentionally ends the in-memory session.

## Implemented workflows

- Organization onboarding; member, administrator and employee-ID sign-in.
- Password recovery request and reset-token entry. The current backend uses a fake email provider; real recovery delivery requires backend work.
- Workspace overview showing the actual organization and signed-in identity.
- Active people directory, 20 records per page, search within the current page, account creation and name/email edits. No invented totals or server-wide search.
- Regions → branches → departments → teams, with parent-scoped listing and creation. Team creation includes the backend-required `department_id`.
- Role listing, creation and inspection of assigned permissions.
- Organization name/handle updates.
- Direct/group conversations, paged history, private file attachments and a conversation-scoped Files view. See [setup and release gates](../docs/MESSAGING_FILES_SETUP.md).
- Loading, empty, validation, permission-denied, network failure, retry and session-expiry states.

This first frontend does not include employee-record administration, role/permission assignment, account deactivation, super-admin operations, hierarchy editing, websocket delivery, presence, or read receipts. These remain explicit follow-on workflows, not inactive controls pretending to work. The broken admin dashboard aggregate endpoint is not used.

## Security and integration

Authorization remains enforced by FastAPI. The API has no current-user capability endpoint, so controls may be visible to users who lack a permission; a denied request displays the backend's error. Administrator sign-in uses its separate endpoint. UI mode does not grant access.

Bearer tokens exist only in React memory, never localStorage, sessionStorage, URLs or logs. Requests omit cookies, reject redirects and time out after 20 seconds. Navigating away cancels list requests. Changed resource identifiers hide old records before new results arrive. Mutations are not automatically retried. There are no remote fonts, analytics or third-party assets. Text is escaped by React.

The 12-character minimum on new passwords is a frontend UX rule, not a replacement for missing backend password validation. Known backend audit findings remain release blockers; this change does not alter authentication or authorization rules.

## Validation

```sh
npm run format:check
npm test
npm run build
npm audit
```

The tests cover the HTTP boundary and hierarchy contracts. Browser checks against an isolated fixture API are documented in `../docs/FRONTEND_DELIVERY.md`; they are not evidence of real database integration. The CI workflow runs formatting, tests, build and dependency audit.

## Hosting contract (not deployed)

`npm run build` produces `dist/`. Serve it over HTTPS and reverse-proxy `/api/*` to FastAPI on the same origin. `vite preview` previews static assets only and does not provide the development API proxy. Configure restrictive CSP and other response security headers in the hosting layer; the frontend needs same-origin scripts/styles/connect requests and no third-party resources. Do not expose the development server in production.

Rollback is removal of the separately hosted frontend bundle; no backend schemas or migrations change.

## Public landing page

`/` is the modern-office landing page. `/sign-in` opens login, `/get-started`
opens the existing organization onboarding form, and `/workspace` requires a
session. Refreshing a protected workspace returns to sign-in. Unknown URLs show
a not-found page. Production hosting must serve `index.html` for these client
routes while forwarding `/api/*` to FastAPI.

Office photos are self-hosted in `public/images` with responsive sources, lazy
loading below the fold, alt text and an image-error fallback. Attribution and
license sources are recorded in `../.interface-forge/LANDING-DESIGN.md`.
The landing page marks all unreleased collaboration features as planned and all
illustrative interface previews as concepts. It makes no customer, metric, legal
page or public-contact claims.

## Brand system

Colors and typography are shared through `src/brand.css`; `Wordmark.tsx` and `Icon.tsx` serve public and authenticated screens. Follow the [brand system and comparative research](../.interface-forge/BRAND-SYSTEM.md) for new pages. See [brand rollout validation](../docs/BRAND_ROLLOUT_REVIEW.md) for tested flows and limitations.
