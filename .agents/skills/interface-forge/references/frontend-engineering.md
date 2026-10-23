# Production frontend engineering

## Architecture

Preserve host stack and package manager. Distinguish server/client responsibilities and avoid unnecessary hydration. Use explicit data schemas, stable interfaces, type safety and predictable components. Keep business logic in existing business layers; presentation components should not silently gain authority to approve or delete records.

## Semantic-first strategy

Use semantic HTML whenever it provides the behavior (button, link, label, fieldset, dialog when appropriate, table with caption/headers). A clickable `div` is not a button. Avoid using ARIA as a substitute for real semantics. Ensure correct accessible names, tab order, focus restoration and non-pointer operation.

## Responsive engineering

- Define breakpoints by **content breakage**, not by blindly adopting a framework grid.
- Use fluid layout techniques, container queries when appropriate, readable line lengths, overflow discipline and preserved focus/scroll behavior.
- Mobile tables: select context-preserving patterns (scrolling with clear affordance, prioritized columns, responsive detail disclosure), not automatic arbitrary card conversion.
- Ensure safe areas, touch targets, onscreen keyboard behavior, zoom/reflow, orientation and user font scaling.

## State completeness

Implement loading, skeleton if useful, empty, no-results, recoverable error, offline/network failure, partial data, permission denied, read-only, success and optimistic conflicts as appropriate. Avoid infinite spinners and falsely confirmed actions. Retain form progress on failed requests when safe.

## Media and assets

Images require relevant alt text or explicit decoration; use correct dimensions/`aspect-ratio` to prevent layout shifts. Use responsive formats and controlled loading priority for hero images. Avoid enormous video/WebGL payloads on constrained devices; give reduced-data and motion fallbacks. Check font subsets, licenses and fallback metrics.

## Dependencies

Inspect `package.json`, installed package versions, project security advisories and license before installing. Prefer existing dependencies if suitable. Never install a UI package just because it is cited in the research materials. For experimental GPU primitives require fallback, verified browser matrix and explicit user value.

## Quality conventions

- Component boundaries reflect responsibility and reuse.
- Keep CSS scoping/selectors and token usage consistent.
- Avoid dead code, inline hardcoded styling sprawl, unnecessary state/effects, nondeterministic UI, and excessive render work.
- Avoid hardcoding fake business data; clearly name mocked examples and segregate from production.
- Ensure no exposed API secrets, unsafe HTML injection, dangerous external URL handling or broken route guards.
- Integrate tests into existing runner, not a new ecosystem without justification.

## Before requesting merge

Check git diff for unrelated changes, format/lint/typecheck/build, functional tests for major user paths, browser and responsive previews when possible, asset license and source notes. If any check cannot run, state it explicitly instead of calling the deliverable production-ready.
