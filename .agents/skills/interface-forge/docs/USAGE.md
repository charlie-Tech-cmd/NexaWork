# Practical workflow / deployment guide

## Getting started

1. Install this whole directory into the skill location supported by your agent.
2. Run `python3 scripts/validate_skill.py .` and the local unit tests.
3. Open the target repo and invoke `interface-forge` explicitly if your agent doesn't auto-select skills.
4. State the task, critical flows, brand constraints, audience, and whether the agent may edit.
5. Review its evidence log, design read, implementation plan and QA reports; inspect actual renders before launch.

## Sample end-to-end request

> Use interface-forge in Full mode on this existing app. Research actual source and comparable interaction patterns, document user journeys and design constraints, propose a distinctly branded direction, then implement in small diffs. Preserve backend permissions and all transaction workflows. Use real content and screenshots where available. Run the project's available tests and visual/accessibility checks. Report Pass/Fail/Not run for every gate. Do not add external UI dependencies without explaining the tradeoff.

## Sample audit-only request

> Use interface-forge in Review mode. Do not modify files. Inspect pages, user flows, keyboard navigation, error states and visual hierarchy. Return P0–P3 issues with evidence, reproducible steps and fixes, and say what could not be tested.

## Handoff artifacts

Copy the templates from `assets/templates/` into a target repository's `.interface-forge/` as needed. These files belong to the project; do not confuse them with the installed skill's own source.

## Limits

The skill does not provide a browser, hosted design service, deploy access, asset license or test runner. Without those tools the agent should generate specifications/source where possible and label unverified checks. It must not promise autonomous visual testing in absent tooling.

## Compatibility note

Agent Skills metadata is portable as a format, but runtime invocation and installation vary by client and version. Verify client documentation before assuming an agent automatically loads the package.
