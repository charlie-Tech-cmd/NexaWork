# NexaWork modern office landing page

> Historical design record. The current redesign, asset provenance and verification are documented in [LANDING_REDESIGN_RPI.md](../docs/LANDING_REDESIGN_RPI.md). The original photos below are retained but no longer rendered.

## Research and art direction

Reviewed main `a39b177` on 2026-10-27 and blueprint sections 37–38. Existing client: React 19, TypeScript, Vite, custom CSS; no router dependency. Reuse the existing Auth/onboarding and workspace APIs. Main has no frontend; this review includes the earlier local frontend foundation commit `1c107de` as a dependency.

Selected direction: welcoming, assured, organized. Original split hero with documentary office photography, navy editorial typography, blue calls to action and restrained interface illustrations. Alternatives: a full-photo hero (less predictable text contrast) and a dashboard-first hero (less human, risks overstating planned functionality). No copied layouts, logos or customer claims.

Dribbble reference research:
- Anna, [SaaS Landing Page Design for Team Collaboration Platform](https://dribbble.com/shots/26588809-SaaS-Landing-Page-Team-Collaboration-Platform): clear message/CTA hierarchy and blue-neutral color system. Page and reference description inspected; its CDN image failed to resolve in the browser.
- Durgesh Ray, [Coworking Space Landing Page UI Design](https://dribbble.com/shots/27350688-Coworking-Space-Landing-Page-UI-Design): office imagery and typography as the first impression. Textual design notes informed the direction.

## System

- Colors: navy #14243d, action #275ee8, body #5e697b, subdued text #627087, soft surface #f5f7fb, white.
- System sans-serif fonts, no external font requests. Fluid headline; readable body text; compact metadata labels.
- Container max 1224px; 48px desktop side space, reduced on small screens. Two-column hero, three-column feature grid → two → one.
- Scoped `.landing-*` layouts consume the shared brand tokens. The subsequent all-page migration is documented in `BRAND-SYSTEM.md`. Reusable SVG icons, button links, responsive photo component, concept preview and availability badge.
- Anchors for sections; real /sign-in and /get-started entries; /workspace requires an in-memory session. History navigation handled without a router dependency.
- Mobile menu is a disclosure (not a modal), supports Escape with focus restoration, and closes on selection/outside click. Native links/buttons and focus outlines throughout.
- Concept previews are labeled sample content, never represented as screenshots. Workday accordion changes the illustrated story and uses aria-expanded/aria-controls.
- Only subtle hover transitions; reduced-motion honored. No carousel, video, trackers or invented statistics.

## Truthful feature inventory

Updated after PR #8 merged at `16fe31e` (2026-10-30): organization onboarding, people create/list/edit, region/branch/department/team create/list, role create/list/permission inspection and organization settings remain implemented. Direct/group messaging now has an available badge. Private file sharing has an explicit “Available when enabled” badge and workspace-administrator enablement note; uploads remain off by default. Channels, announcements, meetings and AI remain Planned. No production activation or deployment is claimed.

The hero, feature cards, workday scenes, benefits, closing copy and HTML description reflect this inventory. Messaging/files cards appear first and receive a restrained blue highlight using existing tokens. Workday illustrations remain labeled sample content. No presence, read receipts, public sharing, invitation delivery or realtime transport claims are added.

Contact: no verified public business contact. The section directs existing users to their organization administrator and states that a public channel is unavailable. Privacy/Terms pages do not exist, so there are no fabricated legal links.

## Asset provenance

Both photos are illustrative office scenes, not NexaWork customers or endorsements. Images are self-hosted at 720px and 1440px, JPEG, each below 250 kB. Hero is eager/high-priority; showcase is lazy. Fixed geometry prevents photo layout shifts; meaningful alt text and an unavailable-photo fallback are provided.

- Hero: Vitaly Gariev, [Diverse team collaborates around a table in office](https://unsplash.com/photos/diverse-team-collaborates-around-a-table-in-office-fm4B1xWEIsU), downloaded 2026-10-27, [Unsplash license](https://unsplash.com/license). CDN source `https://images.unsplash.com/photo-1758873269276-9518d0cb4a0b`. JPEG query uses fit=crop, fm=jpg, w=720/1440, q=78/80.
- Showcase: Christina Morillo, [Group of People Beside Table](https://www.pexels.com/photo/group-of-people-beside-table-1181433/), downloaded 2026-10-27, [Pexels license](https://www.pexels.com/license/). CDN source `https://images.pexels.com/photos/1181433/pexels-photo-1181433.jpeg`. JPEG query uses auto=compress, cs=tinysrgb, w=720/1440, q=78/82.

Visible photographer credit links are included in the footer. Assets are used in a positive illustrative context without implying endorsement. No image generation or remote runtime assets are used.
