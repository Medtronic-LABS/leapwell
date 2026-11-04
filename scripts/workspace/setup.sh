#!/usr/bin/env bash
# Clone the LeapWell code repos into repos/<name>, point their git hooks at leapwell's
# .githooks, and run the tool doctor. Safe to re-run: existing clones are only fetched.
#
# Env: LW_CLONE_BASE overrides the clone URL prefix (default https://github.com/<org>/).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ONLY=""; CLONE=1; SSH=0; STRICT=0

usage() {
  cat <<'USAGE'
Usage: scripts/workspace/setup.sh [options]
  --only key,key   limit to these repo keys (see repos.json)
  --no-clone       do not clone; only configure hooks on existing clones, then run doctor
  --ssh            clone over SSH (git@github.com:<org>/<name>.git) instead of HTTPS
  --strict         exit non-zero if a repo failed or a tool is missing
  --help           show this help
Existing clones are fetched only: never reset, rebased, pulled or switched.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --only) ONLY="${2:-}"; shift 2 ;;
    --no-clone) CLONE=0; shift ;;
    --ssh) SSH=1; shift ;;
    --strict) STRICT=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

org="$(cd "$ROOT" && python3 -m scripts.sdlc.repos --get org)" || exit 1
rows="$(cd "$ROOT" && python3 -m scripts.sdlc.repos --list)" || exit 1

if [ -n "${LW_CLONE_BASE:-}" ]; then BASE="$LW_CLONE_BASE"
elif [ "$SSH" -eq 1 ]; then BASE="git@github.com:$org/"
else BASE="https://github.com/$org/"; fi

wanted() {
  [ -z "$ONLY" ] && return 0
  case ",$ONLY," in *",$1,"*) return 0 ;; esac
  return 1
}

failed=0
report_state() { # dir
  local branch dirty
  branch="$(git -C "$1" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  dirty="clean"
  [ -n "$(git -C "$1" status --porcelain 2>/dev/null)" ] && dirty="DIRTY (left untouched)"
  echo "  branch: ${branch:-unknown}, $dirty"
}

while read -r key name branch; do
  [ -n "$key" ] || continue
  wanted "$key" || continue
  dir="$ROOT/repos/$name"
  echo "== $key ($name)"
  if [ -d "$dir/.git" ]; then
    git -C "$dir" fetch --quiet || { echo "  fetch failed (offline or no access?)"; failed=1; }
    report_state "$dir"
  elif [ "$CLONE" -eq 1 ]; then
    mkdir -p "$ROOT/repos"
    if git clone --quiet --branch "$branch" "$BASE$name.git" "$dir"; then
      echo "  cloned on $branch"
    else
      echo "  clone FAILED (no access or no network?) - continuing"
      failed=1
      continue
    fi
  else
    echo "  not cloned (--no-clone)"
    continue
  fi
  git -C "$dir" config core.hooksPath "$ROOT/.githooks"
done <<< "$rows"

# leapwell's own commits go through the same hooks (the chain skips its own .githooks).
git -C "$ROOT" config core.hooksPath "$ROOT/.githooks"

echo
echo "== tools"
doctor_args=()
[ -n "$ONLY" ] && doctor_args+=(--only "$ONLY")
[ "$STRICT" -eq 1 ] && doctor_args+=(--strict)
(cd "$ROOT" && python3 -m scripts.workspace.doctor ${doctor_args[@]+"${doctor_args[@]}"}) || failed=1

[ "$STRICT" -eq 1 ] && [ "$failed" -ne 0 ] && exit 1
exit 0
