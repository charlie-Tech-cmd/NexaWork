#!/usr/bin/env python3
"""Read-only, heuristic UI project inventory; never opens env files or source bodies.

Prints path names and coarse project evidence. This is NOT a security or visual audit.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

EXCLUDE_DIRS = {
    ".git", ".next", ".nuxt", "node_modules", "dist", "build", "coverage",
    ".turbo", ".cache", ".venv", "venv", "target", ".output", "vendor",
}
EXCLUDE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", "id_rsa",
    "id_ed25519", "secrets.json", ".npmrc", ".pypirc", "credentials.json",
}
SUFFIXES = {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".css", ".scss", ".html"}
SIGNALS = {
    "react": ["package.json", "src/App.tsx", "src/App.jsx"],
    "next": ["next.config.js", "next.config.mjs", "next.config.ts", "app/layout.tsx", "src/app/layout.tsx"],
    "vite": ["vite.config.ts", "vite.config.js"],
    "vue": ["vue.config.js", "nuxt.config.ts"],
    "svelte": ["svelte.config.js", "svelte.config.ts"],
}


def inspect(root: Path, max_files: int = 20000) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {"routes": [], "components": [], "tests": [], "styles": [], "design_docs": []}
    named_root = []
    for candidate in ("package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lockb", "bun.lock", "tsconfig.json", "tailwind.config.js", "tailwind.config.ts", "playwright.config.ts", "vitest.config.ts", "AGENTS.md", "DESIGN.md"):
        if (root / candidate).is_file():
            named_root.append(candidate)
    scanned = 0
    truncated = False
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda p: p.name)
        except (PermissionError, OSError):
            continue
        for path in children:
            if path.is_symlink():
                continue
            if path.is_dir():
                if path.name not in EXCLUDE_DIRS and not path.name.startswith(".git"):
                    stack.append(path)
                continue
            if not path.is_file() or path.name in EXCLUDE_NAMES or path.name.startswith(".env"):
                continue
            scanned += 1
            if scanned > max_files:
                truncated = True
                break
            if path.suffix not in SUFFIXES and path.name not in {"DESIGN.md", "AGENTS.md"}:
                continue
            relative = path.relative_to(root).as_posix()
            counts[path.suffix or "other"] += 1
            low = relative.lower()
            buckets = []
            if ("/app/" in f"/{low}" or "/pages/" in f"/{low}") and path.name.startswith(("page.", "+page.", "index.")):
                buckets.append("routes")
            if "component" in low or "/ui/" in low:
                buckets.append("components")
            if "test" in low or "spec" in low or "__tests__" in low:
                buckets.append("tests")
            if path.suffix in {".css", ".scss"}:
                buckets.append("styles")
            if path.name in {"DESIGN.md", "AGENTS.md"}:
                buckets.append("design_docs")
            for bucket in buckets:
                if len(examples[bucket]) < 15:
                    examples[bucket].append(relative)
        if truncated:
            break
    detected = {k: any((root / name).exists() for name in names) for k, names in SIGNALS.items()}
    return {
        "root": str(root), "scanned_files": min(scanned, max_files), "truncated": truncated,
        "root_config_files": named_root, "framework_hints": detected,
        "file_extensions": dict(sorted(counts.items())), "sample_paths": examples,
        "disclaimer": "Read-only path-level heuristics; no content, secrets, screenshots, build, a11y, security or functionality audited.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Path to local web application")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON")
    parser.add_argument("--max-files", type=int, default=20000)
    args = parser.parse_args()
    if args.max_files < 1:
        parser.error("--max-files must be positive")
    try:
        report = inspect(args.project, args.max_files)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Project: {report['root']}")
        print(f"Files scanned: {report['scanned_files']} (truncated: {report['truncated']})")
        print("Framework hints:", ", ".join(k for k, v in report["framework_hints"].items() if v) or "none")
        print("Configs:", ", ".join(report["root_config_files"]) or "none")
        for category, paths in report["sample_paths"].items():
            print(f"{category}: {', '.join(paths) or '(none sampled)'}")
        print(report["disclaimer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
