#!/usr/bin/env python3
"""Restore pinned repository skills without overwriting local modifications."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(directory: Path, files: dict) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Missing or unsafe skill directory: {directory}")
    actual = set()
    for path in directory.rglob("*"):
        relative = path.relative_to(directory)
        if path.is_symlink():
            raise ValueError(f"Symlink is not permitted: {path}")
        # Ignore generated Python caches; these are never installed or committed.
        if "__pycache__" in relative.parts:
            continue
        if path.is_file():
            actual.add(relative.as_posix())
    if actual != set(files):
        raise ValueError(f"File inventory differs from lock: {directory}")
    for relative, expected in files.items():
        path = directory / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            raise ValueError(f"Content differs from lock: {path}")
        if bool(path.stat().st_mode & 0o111) != expected["executable"]:
            raise ValueError(f"Executable mode differs from lock: {path}")


def install(check: bool, source_root: Path | None) -> None:
    lock = json.loads((ROOT / ".agents/skills.lock.json").read_text())
    if lock["version"] != 1:
        raise ValueError("Unsupported skills lock version")
    target = ROOT / ".agents/skills"
    if target.is_symlink():
        raise ValueError(f"Refusing symlink target: {target}")
    # Validate paths before any file writes or network calls.
    for name, package in lock["skills"].items():
        if name not in {"rpi-production-engineering", "interface-forge"}:
            raise ValueError(f"Unexpected skill: {name}")
        if package["repository"] != f"https://github.com/maxchichar/{name}.git":
            raise ValueError(f"Unexpected source repository: {name}")
        commit = package["commit"]
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            raise ValueError(f"Invalid pinned commit: {name}")
        for relative in package["files"]:
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
                raise ValueError(f"Unsafe locked path: {relative}")
    missing = []
    for name, package in lock["skills"].items():
        destination = target / name
        if destination.exists() or destination.is_symlink() or check:
            verify(destination, package["files"])
            print(f"PASS: {name} matches {package['commit']}")
        else:
            missing.append(name)
    if check or not missing:
        return
    # Prepare and verify both packages before installing either.
    with tempfile.TemporaryDirectory(prefix="nexawork-skills-") as temporary:
        staging = Path(temporary)
        for name in missing:
            package = lock["skills"][name]
            source = source_root / name if source_root else staging / f"source-{name}"
            if source_root is None:
                subprocess.run(["git", "clone", "--no-checkout", package["repository"], str(source)], check=True)
                subprocess.run(["git", "-C", str(source), "checkout", "--detach", package["commit"]], check=True)
            # Copy only locked files, excluding repository metadata and caches.
            prepared = staging / name
            for relative, expected in package["files"].items():
                origin = source / relative
                if any(p.is_symlink() for p in [origin, *origin.parents]):
                    raise ValueError(f"Refusing symlink source: {origin}")
                destination = prepared / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origin, destination)
                destination.chmod(0o755 if expected["executable"] else 0o644)
            verify(prepared, package["files"])
        target.mkdir(parents=True, exist_ok=True)
        for name in missing:
            shutil.copytree(staging / name, target / name)
            print(f"Installed: {target / name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify installed files offline; do not modify anything")
    parser.add_argument("--source-root", type=Path, help="Offline parent directory containing both upstream packages")
    args = parser.parse_args()
    try:
        install(args.check, args.source_root.resolve() if args.source_root else None)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
