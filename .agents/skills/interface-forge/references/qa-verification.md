# Verification playbook — no proof, no pass

## Evidence categories

**Pass** — exact check executed and matched acceptance. **Fail** — exact check executed and did not. **Not run** — unavailable/not attempted; reason. **Not applicable** — scope excludes it; reason. Avoid unsupported blanket claims like "production-ready".

## Tooling selection

Use the project's preinstalled test tools. Common examples: package manager lint/typecheck/build, unit/component tests, Playwright or Cypress E2E, screenshot visual comparisons, axe automated accessibility, browser DevTools/Lighthouse for lab performance, RUM/CrUX for field metrics where available. Do not run destructive data tests on production users; use authorized staging and seeded fixtures.

### Behavioral smoke scenarios

- First visit, return visit, signed-out/access-limited, loading, empty, populated, invalid input, network timeout, retry, success, duplicate submission, expired session, long content, locale/currency changes where relevant.
- On sensitive tasks, check server-authorized role boundary directly, not just whether the menu item appears.
- On redesign, compare pre/post critical flows and baseline tests.

### Responsive matrix

Capture narrow phone, typical phone, tablet, desktop and wide layouts with representative content. Check keyboard overlays, 200%/400% zoom/reflow, orientation and no unintended horizontal scrolling. Viewport sizes are examples and should reflect project support matrix.

### Visual review

Use screenshots from actual running app and representative states. If Playwright snapshot tests are available, compare in same OS/browser context; differences can arise from platform fonts/rendering. Treat snapshots as change detectors, not aesthetic judges. Inspect manually.

### Accessibility

Automated checks plus manual keyboard, focus, screen-reader spot checks and zoom. A zero-violation axe report doesn't certify WCAG. Record known exceptions and scope.

### Performance

Document test environment. Compare baseline/after using repeatable lab traces and field data when available. Field CWV thresholds and 75th-percentile evaluation live in `performance.md`.

## Release report

Use template `assets/templates/QA-REPORT.md` including:
- Build SHA/date/environment/routes tested
- Requirement-to-test traceability
- Pass/Fail/Not run/NA for behavior, responsive, a11y, performance, visual, security, maintainability
- Actual commands and results; screenshots/trace references when available
- P0–P3 issues, fixes/retests, unresolved caveats
- Release decision: Ready / Ready with exceptions / Not ready / Not assessed

**Ready** requires no unresolved P0/P1 and sufficient actual tests for the project's risk profile. If checks didn't run, classify **Not assessed**, not Ready.
