# Landing redesign: research, plan, implementation and verification

Date: 2026-10-30. Baseline: main `e882699` after PR #9. Scope: public landing page.

## Research and acceptance

Visitors should understand NexaWork, explore messaging and file sharing, and reach existing sign-in or organization-setup forms. The previous page had a split photo hero and similarly weighted cards. The user requested a refined design retaining navy/blue colors and a conference scene with mixed skin tones.

Evidence: React/Vite client, `frontend/src/brand.css`, route tests, `docs/MESSAGING_FILES_RPI.md` and `docs/MESSAGING_FILES_SETUP.md`. Official reference pages inspected: [Apple](https://www.apple.com/) for concise product storytelling, [Linear](https://linear.app/) for product-detail previews, [Resend](https://resend.com/) for focused messaging. These are design interpretations; no reference assets, code, logos or claims copied.

Acceptance: preserve colors and auth routes; clearly present messaging/private files; retain accurate enablement/planned labels; show a diverse conference; support keyboard/mobile interactions; avoid overflow at 320–1440px; optimize imagery; verify rendered pages.

## Direction and implementation

Direction: calm, precise, human. Fluid typography, generous space, quiet borders, one human hero image and a detailed product illustration. Existing system-font stack and brand tokens remain; no new application dependencies or remote fonts.

- `frontend/src/landing/Landing.tsx`: centered desktop/left-aligned mobile hero, conference illustration, Messages/Files tabs, feature explanations, organization diagram, compact roadmap, navy closing and footer.
- `frontend/src/landing/landing.css`: replacement responsive styles scoped under `.landing-page`. Dedicated heading classes prevent workspace CSS collisions. Breakpoints 1050/800/600px, existing focus outlines, reduced-motion support.
- `frontend/index.html`: matching title and local SVG favicon.
- `frontend/public/images/conference-{720,1440}.webp`: 46,908/110,282 bytes, responsive sources, fixed geometry, high priority, unavailable-image fallback.
- `frontend/tests/landing.test.ts`: WebP integrity/size budget added to existing route/asset tests.

Preview tabs support pointer, arrows, Home and End. Fictional sample content is labeled explicitly. Sidebar/file entries are illustrations, not simulated send/download controls. Actual links open `/sign-in` and `/get-started`. Mobile menu supports Escape/focus restoration and selection/outside dismissal.

Private files require administrator enablement; downloads are limited to conversation members. No presence/read-receipt/realtime, public-link, production activation, endorsement or usage-statistic claims. Channels, announcements, meetings and AI stay planned.

## Asset provenance

Built-in image generation tool, 2026-10-30. The footer identifies the conference scene as an AI-generated illustration; alt text also calls it an illustration. It does not depict customers. Generated PNG resized/encoded to responsive WebP. Original licensed photos remain in the repository but are no longer displayed.

Final prompt:

> Use case: photorealistic-natural. Asset type: panoramic conference photograph for NexaWork workplace software landing page. Primary request: A candid, beautifully composed diverse team conference in a modern daylight office, with visibly mixed dark, medium and light skin tones, women and men. Six colleagues around a long oak conference table collaboratively discussing a document, open laptops and notebooks. Calm human connection, natural engaged expressions, no posed lineup, no exaggerated smiles. Editorial architectural photography, clean airy contemporary office with warm white walls, broad windows, subtle navy upholstery, muted blue and neutral clothing, refined restrained palette. Composition: wide landscape 16:9, all six people's faces comfortably inside central 85 percent of frame, waist-up and table visible, no extreme foreground obstructions. Soft directional daylight, realistic skin texture, natural hands. This is an illustrative scene, no actual company or recognizable individuals. No text, no logos, no watermarks, no interface overlays.

## Verification

- PASS: strict TypeScript and production Vite build. Main JS 272.56 kB / 82.87 kB gzip; main CSS 44.39 kB / 8.56 kB gzip. Transfer sizes, not field performance metrics.
- PASS: 22 frontend tests; formatting; diff whitespace check; npm audit (0 vulnerabilities).
- PASS: automated local Chrome/Playwright checks at 320, 390, 430, 768, 1280 and 1440 CSS pixels: no horizontal overflow, working tabs, valid section anchors and no console/page errors.
- PASS: arrow/Home/End selection and focus, mobile menu Escape/focus restoration and navigation dismissal, actual sign-in/onboarding forms load, failed-image fallback.
- PASS: axe-core WCAG A/AA automated scans at 390 and 1440px, zero violations in checked states. Screenshots reviewed at desktop/mobile after correcting a global heading-style collision. This is not full accessibility certification.
- NOT RUN: screen-reader sessions, Safari/Firefox, actual browser zoom (320px reflow tested), field Core Web Vitals, production deployment, authenticated message/file operations. The landing preview is illustrative and does not call the feature APIs.
- NOT APPLICABLE: backend tests and database migrations for this presentation-only change.

Reproducible browser smoke check: `frontend/tests/browser/landing.smoke.cjs`. Use separately installed Playwright/Chrome and optional axe-core; no runtime dependency was added. Start the frontend, then set `PLAYWRIGHT_MODULE` to the installed Playwright module, `CHROME_PATH` if using an existing Chrome executable, `AXE_PATH` to axe.min.js, `BASE_URL` (default localhost:3000), and optionally `QA_OUTPUT_DIR`. Run `node tests/browser/landing.smoke.cjs` from frontend. The script writes viewport screenshots, axe findings and its results JSON. Install these test tools in an isolated temporary directory if they are not available.

## Release boundary

This redesign does not certify or activate feature infrastructure. `MESSAGING_FILES_RPI.md` and `MESSAGING_FILES_SETUP.md` limitations remain, including default-disabled uploads, scanner/storage setup and deployment verification. No backend, schema, permission, infrastructure or production-data changes. Revert this frontend commit for rollback; no migration.
