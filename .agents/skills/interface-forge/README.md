# Interface Forge

**A web-first, research-led UI/UX engineering skill for coding agents.**

Build or improve real websites and product interfaces through **Research → Plan → Implement → Verify**. It is framework-agnostic, modular, grounded in product context, and free of mandatory third-party UI libraries or hosted services.

## What this is (and is not)

- A reusable Agent Skills package, with `SKILL.md`, focused reference modules, templates, local scripts, evaluations, and validation tests.
- Design direction, product UX, tokens, implementation, accessibility, performance, security, and visual QA in one coherent process.
- **Not** a guaranteed professional designer, browser test runner, accessibility certification, UI component library, or automatic source-code generator by itself. Agent and project capabilities determine what can execute.

## Install

Copy the **`interface-forge` directory** to an Agent Skills location supported by your agent. Common per-user locations include `~/.codex/skills/`, `~/.claude/skills/`, and `~/.cursor/skills/`; exact support varies by tool/version. Or use the safe helper:

```bash
bash scripts/install.sh codex      # or claude / cursor
# explicit target (does not overwrite):
bash scripts/install.sh --target "$HOME/.codex/skills"
```

The helper copies this directory; if it already exists, it aborts instead of overwriting. Restart/reload the agent if it doesn't discover new skills immediately.

## Validate package

```bash
python3 scripts/validate_skill.py .
python3 -m unittest discover -s tests -v
```

This checks packaging and links, **not** design skill effectiveness or app accessibility. Optional framework-specific project inspection:

```bash
python3 scripts/inspect_project.py /path/to/your/web-app
python3 scripts/inspect_project.py /path/to/your/web-app --json
```

The inspector is read-only and heuristic; its output must be checked by an agent or human.

## Example prompts

- "Use interface-forge. Audit this dashboard's UX and accessibility. Do not modify files. Give prioritized findings and verification steps."
- "Use interface-forge in Full mode to redesign my e-commerce site. Research users and competitors first, preserve the existing checkout, then implement with QA."
- "Use interface-forge to extract a design system from my React app and document the migration risks before touching components."
- "Use interface-forge in Focused mode to correct this form's mobile keyboard and error states."
- "Use interface-forge to improve this portfolio without changing its brand identity or making it look like a generic AI template."

## Folder map

- `SKILL.md` — activation guidance, workflow and quality gates.
- `references/` — on-demand specialist modules, with sources and constraints.
- `assets/templates/` — project memory and QA report templates.
- `scripts/` — zero-dependency Python validation and read-only repo discovery; safe install script.
- `tests/` — smoke/unit tests of the package and tools.
- `evals/` — evaluation cases and human scoring rubric. These are **test specifications**, not completed agent performance results.
- `docs/` — usage, rollout, and future evaluation plan.

## Release status

v1.0.0 is a **validated skill package**, not an independently proven improvement in agent design outcomes. Run the evals against real projects and compare matched control runs before claiming effectiveness.

## Principles

Adapt patterns to context. Avoid generic aesthetics by making deliberate decisions, not banning fonts or components. Preserve existing functionality. Make motion optional. Test with evidence. The defaults target WCAG 2.2 AA and Core Web Vitals, but compliance or scores require real measurement.

## Attribution

The references study, but do not redistribute code from, the linked design projects. See [`references/source-notes.md`](references/source-notes.md). No components from third-party repositories are bundled. Own work licensed MIT; third-party libraries retain their respective terms.
