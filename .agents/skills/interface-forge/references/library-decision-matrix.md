# External reference / library decision matrix (reviewed 2026-10-18)

These are research inputs, **not installed skill dependencies**. Check upstream state and current licenses before each adoption. Never automatically clone, install, or redistribute third-party code.

| Project | Best lesson / use | Adoption rule / major caution |
|---|---|---|
| Superdesign Skill | Codebase-informed direction, iterative design drafts, persistent design context | Optional hosted tool/CLI; do not depend on login or transfer user code without consent |
| Better Design | Tokens, component taxonomy, structured a11y review | Optional MCP; reconcile templates with existing brand rather than cloning brand identity |
| Design Taste | Read brief first, assert art direction, disciplined critique | Don't turn its anti-default heuristics into arbitrary universal style bans |
| UI Layouts | Interaction and component design patterns | Audit individual component semantics/dependencies/licenses |
| Motion Primitives | React/Tailwind animation patterns | Upstream says beta; check API, motion-reduction and performance |
| Trickle UI Kit | CSS-first text motion and SSR safety | Confirm per-component focus/reduced-motion behavior |
| Cursify | Creative cursor effect references | Optional art sites only; preserve native pointer, touch and keyboard behavior |
| Paper Shaders | Procedural visual assets/backgrounds | Apache-2.0 per upstream; pin versions, preserve notices when redistributing source |
| Canvas UI | GPU enhanced overlays | HTML-in-canvas browser support experimental; Commons Clause restriction |
| Hyperiux | Interactive/scrolling effects | Free and Pro effects have distinct license rights; verify before copying |

## Adoption worksheet

Record for each proposed library: feature requirement → existing capability → candidates → lifecycle/version/support → accessibility → browser/SSR → bundle/network/render cost → license/security/privacy → fallback → decision owner → test plan. If the project uses no extra library, that's usually a valid result.
