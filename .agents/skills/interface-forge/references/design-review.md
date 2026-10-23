# Design review rubric and defect-driven iteration

## Six passes, in order

1. **Behavioral correctness**: core journeys, auth, save/retry, empty/error/success, stable data.
2. **IA/UX clarity**: task priority, content hierarchy, discoverability, feedback, copy, recovery.
3. **Visual craft**: typographic roles, grid/rhythm, consistent tokens, distinctive identity, meaningful imagery.
4. **Accessibility**: keyboard, focus, semantics, contrast, zoom, motion, assistive tech.
5. **Performance**: paint, interaction, shifts, script/media cost, device fallbacks.
6. **Security/maintainability**: permissions, data safety, dependencies, technical debt, tests.

No single numeric "premium score" can override a major usability or accessibility failure. Scores are prioritization aids only and must be supported by observable evidence.

## Defect template

- **ID / severity**: P0 (blocker), P1 (major), P2 (moderate), P3 (polish)
- **Where**: route, component, device, state, code path
- **Evidence**: screenshot/test/reproduction + whether actually observed
- **Impact**: who cannot complete which task or is misled
- **Likely cause**: separate fact from hypothesis
- **Fix**: exact actionable implementation direction
- **Verify**: test case and measurable acceptance

## Quality gate stop conditions

P0 or P1 unresolved on a core flow: not production-ready. Regression of permissions, credential exposure, broken checkout/data mutation, keyboard-inaccessible primary action, or false success: P0/P1 as context requires. Lack of any browser/manual testing means visual QA is **Not run**, not "passed".

## Avoid polishing the wrong thing

Critique usefulness before taste. If the user can't find a transaction, better shadows are irrelevant. If the flow works but identity is generic, refine art direction. If the design is beautiful but slow at 3G or motion-disabled, scale down effects.

## Final critique format

Summary of product/context → what was tested → top severity-ranked defects → recommended implementation order → verified improvements → unresolved or unmeasured risks. For design alternatives, show benefits *and* tradeoffs.
