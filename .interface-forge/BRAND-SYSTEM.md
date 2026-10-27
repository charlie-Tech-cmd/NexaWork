# NexaWork brand system and product research

Date: 2026-10-27. Scope: every existing frontend screen, on `feat/modern-office-landing`.

## Brief and baseline

**Provided:** extend the approved navy/blue landing-page brand to all pages and research comparable leading workplace products. **Observed:** the public page used navy/blue, while authentication and the workspace used an independent forest/sage palette, an invented N badge, mixed Unicode icons, and many 8–11px labels. Available routes and backend contracts are documented in `frontend/README.md`. **Inferred:** a consistent identity and clearer navigation will reduce the visual discontinuity when entering the workspace; this has not been validated through user research.

Audience: organization administrators and members. Core paths: learn about NexaWork → onboard/sign in → find people, navigate the organization, inspect roles, edit workspace details. Preserve authentication, tenant enforcement, session expiry, API payloads and feature availability. This is a visual/system migration, not a backend release.

Success criteria: one shared brand palette and wordmark; matching controls and icons across existing pages; readable forms, tables and feedback; no unintended document overflow at 320/390/768/1280px; usable keyboard navigation; existing checks pass. The earlier landing direction is already specified, so alternative brand directions would add little value.

## Comparative research

Primary sources inspected on 2026-10-27. Findings below describe public pages/design guidance, not a private audit of these products or a claim that NexaWork has equivalent maturity.

| Reference | Observed principle | NexaWork decision |
| --- | --- | --- |
| [Atlassian color foundations](https://atlassian.design/foundations/color) | Neutral surfaces carry most of the UI; brand, success and danger have different meanings. Focus and selection are distinct and selection has an additional cue. | Navy identity, blue actions, slate/white work surfaces. Green only for successful outcomes/active status, red for errors. Keep selected markers and separate amber keyboard outlines. |
| [Atlassian design tokens](https://atlassian.design/tokens/design-tokens/) | Shared named values provide a common foundation for components and future changes. | `brand.css` owns semantic colors, font, radii and card shadow. Public-page aliases reference those same values. |
| [Atlassian typography](https://atlassian.design/foundations/typography/applying-typography) | A clear type hierarchy and legible small text support dense interfaces. | Increase the workspace's tiny metadata labels to at least 12px; preserve prominent page headings, readable body text and 16px mobile form inputs. |
| [Slack accessibility](https://slack.com/accessibility) | Keyboard navigation, visual controls, reduced motion and accessible content are part of the product experience. | Visible focus, Escape/outside-click menu dismissal, focus return, named scrollable tables, one visible primary heading per authentication screen, reduced-motion support. This does not certify full accessibility. |
| [Linear features](https://linear.app/features) | Capabilities are grouped around work stages; clear app-entry and signup actions remain easy to find. | Retain straightforward task navigation and one primary action per management page. Keep public onboarding/sign-in entry points and honest implemented/planned labels. |

These principles inform an original NexaWork system. No competitor assets, logos, testimonials, statistics, or feature claims are imported.

## Direction and tokens

Identity: **welcoming, assured, organized**. The public page introduces the workplace; authentication repeats its real office imagery; the application favors calm, readable work surfaces. System fonts avoid external requests. Minimal color transitions honor reduced motion.

| Role | Value | Application |
| --- | --- | --- |
| Identity / inverse surface | `#12243e` | Sidebar and authentication story |
| Primary text | `#14243d` | Page titles, labels, content |
| Action | `#275ee8` | Primary buttons, links, active navigation |
| Action hover / pressed | `#174ac9` / `#123ca5` | Interactive feedback |
| Muted text | `#5e697b` | Supporting copy and metadata |
| Work surface / canvas | `#ffffff` / `#f5f7fb` | Cards, forms, page background |
| Selection | `#eaf0ff` | Selected controls and supporting panels |
| Input boundary | `#8592a6` | Identifiable form controls |
| Focus | `#bc6a13` | Keyboard outline, separate from selection |
| Success text / surface | `#236344` / `#edf7f0` | Active badges and successful saves |
| Error text / surface | `#983b2c` / `#fff2ee` | Permission, validation and network failures |

Control radius 8px; panel radius 12px. A reusable text wordmark replaces the invented badge. SVG icons share a 24px viewBox and 1.65px stroke, with visible labels for actions. Informational notices use blue; success notices and Active status use green; inactive is neutral. Disabled controls remain visibly disabled.

## Page and state coverage

- Public homepage and not-found: shared tokens and wordmark, existing product truth preserved.
- Sign-in (member/admin/employee), onboarding, recovery, reset: same navy/white composition, blue actions, labels and feedback. Authentication uses the existing licensed 720px office photo with alt text and a graceful image-failure state. Source/license remains in `LANDING-DESIGN.md`.
- Overview: blue-tinted welcome area, matching icons, readable quick actions and organization summary.
- People: unified search, paginated table, add/edit forms, loading, empty, success and permission/error states. The table alone may scroll horizontally and is keyboard focusable.
- Organization: matching cards, breadcrumbs, region/branch/department/team steps, creation forms and empty states. Steps become a two-column grid on mobile.
- Roles: list, selected state, creation form and permission detail use the same system.
- Settings: consistent organization form and account summary.
- Mobile workspace: persistent text wordmark, collapsible navigation, Escape returns focus to Menu; choosing a page moves focus to its content. Short-height screens omit the optional sidebar note so navigation/account controls remain accessible.

## Engineering boundary

Existing React/TypeScript/Vite architecture; no new dependencies, routes, API calls, credentials or storage. CSS migrations replace the old palette rather than layering a second theme. Shared Wordmark and Icon components are reused across public and authenticated views. No dark-mode preference is introduced. No backend code, permissions or tenant identifiers change. Revert this milestone commit to restore the previous appearance without a data migration.

Verification and limitations: see `docs/BRAND_ROLLOUT_REVIEW.md`.
