# Product UX, information architecture, and interaction specification

## Task-oriented architecture

Structure information around tasks, not internal organizational departments. Prioritize frequently used, high-impact workflows; preserve advanced user shortcuts while allowing novices to learn. Model user roles and permissions separately from visual layouts.

For every critical flow specify:

1. **Trigger and intent** — user goal and entrypoint.
2. **Prerequisites** — authentication, setup, device, known data.
3. **Happy path** — smallest legitimate sequence with feedback.
4. **Alternative paths** — missing info, corrections, saved progress, cancellation.
5. **Failure** — API error, expired session, file too large, unavailable network, validation, conflict, permission denial.
6. **Completion and recovery** — reliable proof of result, undo/retry/help.
7. **Instrumentation** — event names that do not leak personal information.

### Navigation and information scent

- Label destinations in users' words; avoid ambiguous icon-only navigation unless accessible naming and discoverability are addressed.
- Ensure a consistent path back, account/context switching, and clear selection/state indication.
- Do not hide mission-critical operations under hover-only effects or gesture-only navigation.
- For information-dense UIs, expose hierarchy through grouping, headings, table semantics, filters, saved views, and explicit scope/time period.

### Component state contract

For every interactive component specify at minimum: default, hover when relevant, keyboard focus, active, selected, disabled (why), loading, error, success, empty, read-only, and overflow where meaningful. For dialogs: focus enter/trap/return, Escape behavior, destructive confirmation, scroll locking. For menus: arrow-key behavior where relevant; avoid arbitrary custom ARIA when native semantics suffice.

### Forms

- Prefer explicit labels over placeholder-only labels. Group related fields semantically.
- Validate at appropriate times; show inline issue-specific, actionable errors; preserve entered data.
- Clarify mandatory/optional, accepted file formats, limits, timezone, currency units, fees, and privacy consequences.
- Protect double submission, stale state and destructive changes; show genuine server-confirmed success only.
- Use autocomplete and input modes appropriate for locale and device; don't invent phone/address formats.

### Writing is UX

Buttons are verbs describing effect; status messages distinguish pending from saved/confirmed; errors state what failed and what to do next. Never use fabricated credibility signals (e.g., "trusted by 10,000") or fake activity. Choose terms users recognize. Keep primary CTA consistent with the actual action.

### Localization and resilience

Test long strings, variable numeral/currency/date formats, translation expansion, RTL when supported, user timezones, and unreliable networks. Avoid assuming everyone has fast connectivity or an always-on mouse. For localized financial UIs: explicit currency, settlement date/timezone, transaction state, source and uncertainty.

### UX acceptance criteria example

"A staff reviewer can identify an unresolved transaction, inspect evidence, add a finding, and submit for manager review using keyboard only; an unauthorized staff member cannot finalize closure; offline/error states preserve unsent comments or clearly warn before data loss." This is stronger than "modern dashboard."
