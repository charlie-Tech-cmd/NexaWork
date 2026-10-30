# Brand rollout — review milestone

Date: 2026-10-27. Branch: `feat/modern-office-landing`. PR: https://github.com/charlie-Tech-cmd/NexaWork/pull/3

## Change

The public landing page used navy/blue while the authentication and workspace screens used an unrelated green palette. All existing pages now share semantic color tokens, a text wordmark, SVG icons, consistent controls and readable metadata. Authentication reuses the licensed office photograph. Mobile navigation includes the wordmark, Escape dismissal and focus return. The organization hierarchy becomes two columns on small screens.

Browser review also identified and fixed two visible defects: an absolutely positioned screen-reader table label caused document overflow on narrow screens; the table now contains it. The settings save confirmation was lost when its form unmounted during an organization refresh; the notice now lives in the workspace and remains visible after refresh, clearing on navigation.

Research, token roles, page inventory and rationale: [Brand system](../.interface-forge/BRAND-SYSTEM.md). This builds on the earlier landing-page review. Backend routes, tenant isolation, role checks, in-memory session storage and the implemented/planned feature boundary are unchanged. No dependencies or backend files changed.

## Validation

- PASS — existing 13 frontend tests (HTTP boundary, errors, credentials, hierarchy contracts, public routes and image integrity).
- PASS — production build, including strict TypeScript checking. JavaScript approximately 268 kB / 81 kB gzip; CSS approximately 42 kB / 9 kB gzip.
- PASS — Prettier format check and `git diff --check`. No standalone frontend linter is configured.
- PASS — npm audit: zero reported vulnerabilities.
- PASS — browser visual review of homepage, sign-in variants, onboarding/recovery/reset forms, overview, people/add/edit, region/branch/department/team hierarchy, roles/create/detail, settings and not-found styling.
- PASS — representative desktop 1280px, tablet 768px, mobile 390px and narrow 320px checks. People document width equals viewport after the fix; the table has its own scroll area. Organization steps and long onboarding forms fit at 320px.
- PASS — fixture-backed sign-in/out; test-person save; organization save confirmation after refresh; hierarchy traversal and empty teams; no-match people search; selected role permissions; permission-denied/retry; expired-session return to sign-in.
- PASS — public mobile navigation and sign-in entry, labeled controls, visible primary auth heading, menu Escape/focus return, named and focusable directory scroll region, selected state cues. Native table arrow-key scrolling was not confirmed by browser automation.
- PASS — measured palette contrast: primary text on white 15.56:1; muted on white 5.55:1 and canvas 5.18:1; white on blue 5.45:1; blue on selected surface 4.78:1; inverse muted on raised navy 7.98:1; success text/surface 6.52:1; error text/surface 6.40:1. Input outline/white 3.15:1; focus ring/white 4.03:1 and navy 3.87:1.
- PASS — browser console check returned no warning/error entries during the checked flows. Self-hosted photo assets loaded.

## Evidence and boundaries

Browser verification used the local frontend with a disposable API fixture explicitly named “Test workspace · QA only.” It verifies presentation and request/response behavior, not real database persistence or production authorization. No real organization or user record was created or edited. Test screenshots are retained with task outputs (`nexawork-brand-overview.png`, `nexawork-brand-roles-mobile.png`, `nexawork-brand-sign-in.png`).

NOT RUN — live backend end-to-end acceptance, production onboarding or email delivery, automated axe scan, screen-reader certification, full browser/device matrix, actual 200%/400% browser zoom, measured field performance/Core Web Vitals. Narrow viewport checks are not a substitute for zoom/assistive-technology checks. Existing backend audit findings remain separate release considerations.

NOT APPLICABLE — backend migrations and deployment for this frontend design milestone. Nothing merged or deployed. Review against blueprint sections 37–38 before merging; the next priority is full integration acceptance against a runnable nonproduction backend.
