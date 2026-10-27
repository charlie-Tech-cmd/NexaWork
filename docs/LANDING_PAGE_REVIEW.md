# Modern office landing page — review milestone

Date: 2026-10-27. Target: main at a39b177. Branch: feat/modern-office-landing.

## Problem and change

Main has no browser client, and the existing local frontend opened directly at login. Visitors need a credible introduction to NexaWork and a clear path into organization setup without being misled by the product blueprint's roadmap.

This PR includes the existing React/TypeScript workspace foundation (commit 1c107de, previously local only) plus a dedicated public landing page. No backend code or authorization rules change. Review the foundation and landing milestone as separate commits.

Public routes: `/` landing, `/sign-in` login, `/get-started` organization onboarding, `/workspace` authenticated client. Unknown routes have a not-found screen. Native anchors handle section navigation; history handling adds no dependency. Production must use SPA fallback for public routes and forward `/api` separately.

## Blueprint alignment and product truth

Blueprint sections 37–38 request modern, responsive, accessible enterprise UI. The implementation follows the existing React architecture, uses navy/blue tokens scoped to the public page, and retains existing workspace components and API boundaries.

Implemented: organization onboarding, people create/list/edit, organization hierarchy create/list, role creation/list/permission inspection, organization settings. Messaging is not merged into main; channels, announcements, meetings, file sharing and AI are not implemented there. All six requested feature cards say Planned, with clear section-level and hero availability notes. The workday showcase distinguishes an available foundation from planned scenes and labels its miniature interfaces “Illustrative concept · sample content.”

The hero and closing copy match the requested headlines and tagline. Real office photos are optimized and self-hosted, with source/license records in `.interface-forge/LANDING-DESIGN.md`. No invented logos, customer testimonials, statistics, business contacts or legal URLs. Contact points existing members to their organization administrator and says a public channel is unavailable.

## Verification

- PASS: `npm run format:check`.
- PASS: `npm run build` (strict TypeScript check plus Vite production build).
- PASS: `npm test` — 13 tests covering the API boundary, public route resolution, unknown routes and image integrity/size limits.
- PASS: browser review at 1280px desktop, 768px tablet, 390px mobile. Narrow 320px check recorded in task evidence.
- PASS: image completion and local sources, all section anchors resolve, feature availability labels visible, workday accordion changes its concept content.
- PASS: mobile menu disclosure, Escape dismissal and focus restoration; Get Started opens the actual onboarding form; sign-in and protected route checks recorded in task evidence.
- PASS: browser console inspection showed no warnings/errors during the checked landing flows.
- PASS: measured main text/action contrast pairs; low-contrast small neutral labels were darkened. Body #5e697b on white is 5.55:1; action #275ee8 with white is 5.45:1. This is not a full WCAG certification.
- No standalone frontend linter is configured; formatting and strict TypeScript checks were run instead. No dependency was added for this landing page.
- NOT RUN: production deployment, complete assistive-technology/multi-browser certification, real backend onboarding submission and production performance measurement. The earlier local backend dependency limitation remains; this PR does not claim to repair it.

Build output is approximately 266 kB JavaScript (81 kB gzip) and 39 kB CSS (9 kB gzip). Each office-image variant is below 180 kB; mobile variants are approximately 51/65 kB. These are transfer-size observations, not measured Core Web Vitals.

## Review / rollout boundary

Submit for maintainer review against the blueprint before merging. No merge or deployment is authorized or attempted. Existing backend audit findings remain separate release blockers. Reverting the frontend commits removes the change without a database migration.
