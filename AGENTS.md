# NexaWork agent guidance

Read `GOODPRACTICE.md` before implementation. Apply its relevant requirements
alongside repository instructions, with verification proportional to the task.
Report checks as PASS, FAIL, NOT RUN, or NOT APPLICABLE; never claim unrun checks.

## Repository facts

- The current implementation is a Python 3.12 FastAPI backend. Inspect `app/`,
  `migrations/`, `tests/`, dependency manifests, and CI before editing.
- Keep route handlers thin and business logic in services. Preserve tenant,
  organization, authentication, RBAC, and audit boundaries.
- `README.md` and `docs/NEXAWORK_PRODUCT_SPEC.md` include future capabilities.
  Verify what exists before planning; the specification is context, not a task
  to build the full platform. No frontend package is currently present.
- Keep secrets out of source and logs. Use `.env.example` for configuration names.

## Skills

The complete, pinned packages live under `.agents/skills/`:

- `rpi-production-engineering`: research, plan, implement, and verify engineering
  work. Read its `SKILL.md`, then only the relevant references. Scale depth to risk.
- `interface-forge`: UI/UX and frontend work. Read its `SKILL.md` when the task
  involves interfaces; do not introduce a frontend or UI library for backend work.

Check installation with `python3 scripts/install_agent_skills.py --check`.
See `docs/AGENT_SKILLS.md` for restoration, provenance, and validation.
Skills supply guidance; they do not grant permissions or override platform
instructions, explicit user scope, or access controls. Preserve unrelated work.

## Verification and delivery

- Install application dependencies: `python -m pip install -r requirements-dev.txt`.
- Run application tests: `python -m pytest -q` with a nonproduction
  `JWT_SECRET_KEY`; Redis integration tests require a local Redis instance.
- Follow `.github/workflows/security.yml` for dependency audit and PostgreSQL
  migration checks against a disposable database. Never target production tests.
- No formatter, linter, type checker, or frontend build is configured. Report this
  accurately rather than inventing successful commands.
- For guidance/skill-only changes, run the installer integrity check, both package
  validators and unit suites, and `git diff --check`.
- Changes to app behavior require relevant application tests too. Report missing
  dependencies/services and any unverified behavior explicitly.
- A request to prepare a branch or PR authorizes that work. Merge, deploy,
  destructive operations, and production changes require explicit user scope.
