# Agent integration and operating constraints

## Interoperability

Package follows the Agent Skills convention: `SKILL.md` frontmatter and Markdown body, optional `references/`, `scripts/`, `assets/`. Depending on client, project-level/per-user installation locations and auto-discovery differ. Common paths: `~/.codex/skills/interface-forge/`, `~/.claude/skills/interface-forge/`, `~/.cursor/skills/interface-forge/`. Check current tool documentation; no claim of identical triggers across vendors.

## Using RPI with other skills

This skill specializes in frontend/UX. It does not override a project's own testing, security, backend, or architecture policies. In a workflow with a separate general RPI engineering skill: interface-forge owns design research, UI system and visual/interaction verification; the general skill owns infrastructure, broad system architecture and business implementation. Share artifacts and test evidence rather than duplicate meetings.

## External tools are optional

If browser/screenshot tools exist, inspect rendered output; otherwise state the absence of visual inspection. If user supplies reference URLs, visit only with available, authorized browsing. Never pretend that the agent can operate Figma/Canva or install dependencies without relevant tools/permissions. If no repository mounted, output a usable design specification or source artifact within current capabilities rather than falsely claiming changed files.

## Safe operation

Run `scripts/inspect_project.py` for a read-only high-level map. Never print secrets or full `.env` files. Before actions affecting data or deployments, verify expected permissions. Require explicit authorization for third-party account integration, production edits, deleting files or large migrations; ordinary authorized local edits do not need a second round of approval.

## Progressive disclosure and context

Start with `SKILL.md`. Read only relevant references for task mode. Do not blindly dump all modules into the model context. Keep project memory in `.interface-forge/` when it will be useful across iterations. Write short, evidence-backed decisions.
