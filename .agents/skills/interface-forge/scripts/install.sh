#!/usr/bin/env bash
# Safe non-overwriting local installation of this skill.
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "$#" -eq 1 ]; then
  case "$1" in
    codex) BASE="$HOME/.codex/skills" ;;
    claude) BASE="$HOME/.claude/skills" ;;
    cursor) BASE="$HOME/.cursor/skills" ;;
    *) echo "Usage: bash scripts/install.sh {codex|claude|cursor} OR --target PATH" >&2; exit 2 ;;
  esac
elif [ "$#" -eq 2 ] && [ "$1" = "--target" ]; then
  BASE="$2"
else
  echo "Usage: bash scripts/install.sh {codex|claude|cursor} OR --target PATH" >&2
  exit 2
fi
if [ -z "$BASE" ]; then echo "Target must not be empty" >&2; exit 2; fi
mkdir -p "$BASE"
BASE="$(cd "$BASE" && pwd)"
TARGET="$BASE/interface-forge"
if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  echo "Refusing to overwrite existing skill: $TARGET" >&2
  exit 3
fi
cp -R "$SOURCE_DIR" "$TARGET"
echo "Installed Interface Forge to: $TARGET"
echo "Reload your agent if necessary."
