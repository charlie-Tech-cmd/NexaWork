# Accessibility — target WCAG 2.2 Level AA

Baseline is WCAG 2.2 AA as a design/engineering target, *not* a claim of certified conformance. Contextual legal or contractual standards may add requirements. Use the current W3C specification for normative wording: https://www.w3.org/TR/WCAG22/.

## Practical audit groups

**Perceivable:** semantic heading order; text alternatives; meaningful table headers and form labels; captions/transcripts where applicable; information not conveyed by color alone; 4.5:1 normal text contrast and 3:1 large text where success criterion applies; non-text UI contrast; readable text over imagery, adequate spacing, orientation and reflow.

**Operable:** keyboard access; visible focus indicator; focus not entirely obscured by sticky content; no keyboard traps; skip navigation; predictable dialogs and menus; target size/spacing. WCAG 2.2 AA 2.5.8 has a 24×24 CSS px minimum with stated exceptions; 44×44 is a useful ergonomic goal, not a blanket AA rule. Alternative input for drag interactions; avoid motion-triggered controls without mitigation.

**Understandable:** consistent navigation and labels, clear instructions, accessible errors with identification/correction advice, prevention/confirmation for high-impact submissions, distinguish disabled/read-only states, consistent help.

**Robust:** semantic HTML first; correct name, role, state and value; live regions reserved for meaningful updates; don't reimplement native controls unnecessarily. ARIA must be tested with assistive technology, not added decoratively.

## Test matrix

- Keyboard Tab / Shift+Tab / Enter / Space / arrows where relevant / Escape and focus restoration.
- Screen reader spot checks appropriate to OS/browser if available; include landmarks, form errors, menu state and data-table headers.
- 200% text resize and 400% zoom/reflow scenarios within applicability.
- High contrast/forced colors when feasible, light/dark, and prefers-reduced-motion.
- Touch/drag alternatives and pointer target spacing.
- Error states and components dynamically inserted/removed.

## Automation is partial

With existing Playwright setup, `@axe-core/playwright` can catch a subset of issues; manual testing and, for critical products, research with assistive technology users remains needed. See https://playwright.dev/docs/accessibility-testing. Do not say "WCAG passed" from an axe scan alone. Log untested cases as **Not run**.

## Acceptance template

Test: component/route + viewport + browser/AT + expected keyboard/focus/announcement behavior + observed result + screenshot/log evidence + severity + owner. Fix P0/P1 access failures before a production-ready claim.
