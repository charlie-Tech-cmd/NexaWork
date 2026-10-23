#!/usr/bin/env python3
"""Validate local Interface Forge package structure; stdlib only.

Not a replacement for official agentskills/skills-ref schema validation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"(?<!\!)\[[^\]\n]+\]\(([^)]+)\)")
REFERENCE_PATTERN = re.compile(r"`((?:references|assets/templates|scripts)/[A-Za-z0-9_./-]+)`")
REQUIRED = (
    "SKILL.md", "README.md", "LICENSE",
    "references/research-protocol.md", "references/qa-verification.md",
    "assets/templates/DESIGN-SYSTEM.md", "scripts/inspect_project.py",
    "scripts/install.sh", "evals/cases.jsonl",
)


def parse_frontmatter(contents: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not contents.startswith("---\n"):
        return {}, ["SKILL.md must start with --- YAML frontmatter"]
    closing = contents.find("\n---\n", 4)
    if closing < 0:
        return {}, ["SKILL.md is missing closing --- frontmatter marker"]
    raw = contents[4:closing]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith(" ") or line.startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"Invalid frontmatter line: {line!r}")
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    for field in ("name", "description"):
        if not fields.get(field):
            errors.append(f"Frontmatter missing non-empty {field}")
    name = fields.get("name", "")
    if len(name) > 64 or (name and not NAME_PATTERN.fullmatch(name)):
        errors.append("Frontmatter name must be 1–64 lowercase letters/numbers/hyphens")
    if len(fields.get("description", "")) > 1024:
        errors.append("Frontmatter description exceeds 1024 characters")
    return fields, errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"Skill directory not found: {root}"]
    for item in REQUIRED:
        if not (root / item).is_file():
            errors.append(f"Missing required file: {item}")
    skill = root / "SKILL.md"
    if not skill.is_file():
        return errors
    contents = skill.read_text(encoding="utf-8")
    _, meta_errors = parse_frontmatter(contents)
    errors.extend(meta_errors)
    if len(contents.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines: move detail to references/")
    for pointer in REFERENCE_PATTERN.findall(contents):
        if ".." in Path(pointer).parts:
            errors.append(f"Unsafe reference path: {pointer}")
        elif not (root / pointer).is_file():
            errors.append(f"SKILL.md references missing file: {pointer}")
    for markdown in root.rglob("*.md"):
        if any(part.startswith(".") and part != ".github" for part in markdown.relative_to(root).parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            # Ignore anchor and external link destinations; external links are not fetched.
            dest = target.split("#", 1)[0]
            if not dest or re.match(r"^[a-z][a-z0-9+.-]*://", dest, re.I) or dest.startswith("mailto:"):
                continue
            if dest.startswith("/"):
                continue  # application routes may be absolute
            resolved = (markdown.parent / dest).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"Broken local link in {markdown.relative_to(root)}: {target}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    issues = validate(root)
    for issue in issues:
        print(f"ERROR: {issue}", file=sys.stderr)
    if issues:
        print(f"FAIL: {len(issues)} issue(s)", file=sys.stderr)
        return 1
    print(f"PASS: skill structure, metadata and local file references validated ({root})")
    print("NOTE: Real app tests, visual quality and WCAG/CWV compliance are not established by this check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
