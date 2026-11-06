#!/usr/bin/env bash
# Shared helpers for scripts/github/*.sh (sourced, not executed).
# Repo facts come from repos.json via scripts.sdlc.repos; every value is overridable
# from the environment for forks.

# Repo root, independent of the caller's cwd.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

manifest_get() {
  (cd "$REPO_ROOT" && python3 -m scripts.sdlc.repos --get "$1")
}

# "key name integration_branch" per code repo.
manifest_repos() {
  (cd "$REPO_ROOT" && python3 -m scripts.sdlc.repos --list)
}

OWNER="${OWNER:-$(manifest_get org)}"
REPO="${REPO:-$(manifest_get tracker)}"
PROJECT="${PROJECT:-$(manifest_get project)}"
APPLY=0

# Print the mutating command in dry-run; execute it with --apply.
run() {
  if [ "$APPLY" -eq 1 ]; then
    echo "+ $(quote_cmd "$@")"
    "$@"
  else
    echo "[dry-run] $(quote_cmd "$@")"
  fi
}

# Shell-quote arguments so a printed command is copy-pasteable.
quote_cmd() {
  printf '%q ' "$@"
}

# Like run(), but the first argument is a body fed to the command on stdin.
run_stdin() {
  local body="$1"
  shift
  if [ "$APPLY" -eq 1 ]; then
    echo "+ $(quote_cmd "$@")<<'JSON'"
    printf '%s\n' "$body"
    echo "JSON"
    printf '%s\n' "$body" | "$@"
  else
    echo "[dry-run] $(quote_cmd "$@")<<'JSON'"
    printf '%s\n' "$body"
    echo "JSON"
  fi
}

# Parse the flags shared by every script; unknown flags are collected in REST.
# usage: parse_common_flags usage_fn "$@"
REST=()
parse_common_flags() {
  local usage_fn="$1" arg
  shift
  for arg in "$@"; do
    case "$arg" in
      --apply) APPLY=1 ;;
      -h|--help) "$usage_fn"; exit 0 ;;
      *) REST+=("$arg") ;;
    esac
  done
}

# Exit 2 on any argument still left in REST (scripts with no extra flags).
reject_unknown_args() {
  if [ "${#REST[@]}" -gt 0 ]; then
    echo "unknown argument: ${REST[0]}" >&2
    exit 2
  fi
}

banner() {
  if [ "$APPLY" -eq 1 ]; then
    echo "== APPLY mode: changes WILL be made to $OWNER/$REPO =="
  else
    echo "== DRY-RUN (default): nothing is changed. Re-run with --apply to execute. =="
  fi
}
