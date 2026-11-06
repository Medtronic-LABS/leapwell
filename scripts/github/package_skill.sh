#!/usr/bin/env bash
# Package the lw-ticket skill for upload as an org skill. Dry-run by default.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
  cat <<USAGE
Usage: scripts/github/package_skill.sh [--apply] [--help]

Zips .claude/skills/lw-ticket into dist/skills/lw-ticket.zip (the folder is the zip root).
Default is a dry-run that only prints the commands.
USAGE
}

parse_common_flags usage "$@"
reject_unknown_args
banner

SKILL_DIR="$REPO_ROOT/.claude/skills/lw-ticket"
OUT_DIR="$REPO_ROOT/dist/skills"
OUT_ZIP="$OUT_DIR/lw-ticket.zip"

if [ ! -d "$SKILL_DIR" ]; then
  echo "Skill folder not found: $SKILL_DIR" >&2
  exit 1
fi

run mkdir -p "$OUT_DIR"
run rm -f "$OUT_ZIP"
if [ "$APPLY" -eq 1 ]; then
  (cd "$REPO_ROOT/.claude/skills" && zip -r -q "$OUT_ZIP" lw-ticket -x '*/__pycache__/*' '*.DS_Store')
  echo "Wrote $OUT_ZIP"
else
  echo "[dry-run] (cd .claude/skills && zip -r -q $OUT_ZIP lw-ticket -x '*/__pycache__/*' '*.DS_Store')"
fi
