# Research protocol and evidence discipline

## Minimum scope read

Capture: product/organization; primary user role and skill level; job-to-be-done and frequency; success criterion; business objectives; currently used channels; target device and connectivity; time/cost of errors; existing brand/assets; implementation environment; localization and accessibility needs; deadlines and constraints.

For existing projects, inspect structure before proposing a redesign. Read `package.json` or equivalent, routes, CSS variables/themes, shared components, auth boundaries, validation, types, tests and docs. Inspect representative pages and images when rendered access exists. Inventory user-facing errors and feature states.

Use the read-only reconnaissance helper if useful. It cannot tell you how the app actually looks or behaves. Do not send repository source to unrelated external services without user authorization.

## Evidence labels

- **Observed:** verified in inspected code, screenshots, functioning app, measured test, or dated documentation; link to path/route/test.
- **Provided:** directly from the brief/user-provided artifacts; quote accurately.
- **Inferred:** plausible reasoning from evidence, explicitly marked.
- **Unknown:** unvalidated hypothesis that matters to the decision.

Never convert hypotheses into research findings. Do not invent interviews, market demand, user conversion numbers, competitor capabilities, or customer quotes.

## Competitive & reference research

1. Pick 2–4 credible comparators matching product stage, user task, trust requirement, region and device—not only visual look.
2. Evaluate navigation/information scent, task flow, content structure, forms, state handling, typography, visual hierarchy, mobile behavior, accessibility and performance trade-offs.
3. Write what to **adopt**, **adapt**, and **avoid**, with evidence and rationale.
4. Extract a principle, not another site's logo, marketing claims, images, code, copyrighted copy, or bespoke artwork.
5. Verify licensing for assets and integrations separately. If web access unavailable, explicitly label desk hypotheses and skip invented external findings.

## Research deliverable

Write or update `.interface-forge/PRODUCT-UX.md` when context will be reused. Include:
- One-sentence job-to-be-done and business result.
- Primary and secondary personas/roles, identifying which are assumptions.
- The critical journey (entry → locate → act → feedback → recover), and likely drop-off or costly error points.
- Current evidence, constraints, sources, unknowns.
- Requirements ranked Must/Should/Could/Won't, with what must remain unchanged.
- Risks: cognitive burden, trust, bandwidth, account permissions, regulatory concerns, accessibility.
- Success criteria (measurable if instrumented) and falsification tests.

## Decision discipline

For a decision, capture: options, explicit constraints, expected user/business impact, accessibility, tech cost, reversibility, evidence confidence (high/medium/low with why), and how to verify. Big unknowns warrant research or a prototype. Avoid declaring a preference as universal best practice.

## Exit checklist

- [ ] User, task, risk and desired result clear
- [ ] Context sources separated from assumption
- [ ] Existing flows inventoried; protection constraints named
- [ ] Reference patterns evaluated rather than copied
- [ ] Accessibility, locale and connectivity considered
- [ ] Brief can be implemented without further broad interpretation
