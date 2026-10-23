# Research sources and factual caveats

Reviewed 2026-10-18. The following resources informed the original instructional framework, which does **not** copy or package their code.

## Skill authoring

- Open Agent Skills specification — https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx — `SKILL.md` frontmatter; focused files; progressive disclosure.
- OpenAI Skills guide — https://developers.openai.com/api/docs/guides/tools-skills — compatibility with Agent Skills.
- Anthropic skill authoring best practices — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices — concise instructions and metadata constraints.

## UI/design engineering references

- Superdesign Skill — https://github.com/superdesigndev/superdesign-skill — codebase context and design drafts; tool-specific flows require its own CLI/account.
- Better Design — https://github.com/marvkr/better-design — design tokens, MCP and component/a11y guidance.
- Design Taste — https://github.com/madebymustafa/design-taste — explicit art direction, craft and review.
- Canvas UI — https://github.com/DavidHDev/canvas-ui — browser/fallback cautions; MIT + Commons Clause license.
- Paper Shaders — https://github.com/paper-design/shaders — canvas/WebGL effects; Apache-2.0 at review (verify current repo, as mirrors/older versions differ).
- Hyperiux Components — https://github.com/Hyperiux-Immersion-Labs/hyperiux-components — free Effects License distinct from Pro proprietary license and MIT-licensed CLI.
- UI Layouts — https://github.com/ui-layouts/uilayouts — reusable component/effect ideas.
- Motion Primitives — https://github.com/ibelick/motion-primitives — motion component library; beta per README at review.
- Cursify — https://github.com/ui-layouts/cursify — experimental cursor-interaction patterns.
- Trickle UI Kit — https://github.com/akaieuan/trickle-UI-kit — CSS-first SSR-friendly text-motion patterns.

## Technical standards / measurement

- WCAG 2.2 (W3C) — https://www.w3.org/TR/WCAG22/ — use normative text; do not confuse 24 CSS px target-size AA exceptions with a universal 44 px requirement.
- Web Vitals (Google) — https://web.dev/articles/vitals — good thresholds at 75th percentile segmented mobile/desktop.
- Playwright accessibility testing — https://playwright.dev/docs/accessibility-testing — axe automated coverage is incomplete.
- Playwright screenshot comparisons — https://playwright.dev/docs/test-snapshots — golden snapshots require stable environment and human interpretation.

Documentation changes. Re-verify before adoption and do not represent this file as a current, comprehensive security audit of upstream repositories.
