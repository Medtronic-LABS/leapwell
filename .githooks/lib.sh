# shellcheck shell=sh
# Shared by commit-msg and pre-commit (sourced). Resolves leapwell's root from the
# hook's own path, so it works from any repos/<x> clone whose core.hooksPath points here.
LW_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

# chain_repo_hook <hook-name> [args...]: run the repo's own hook setup (stdin passed through).
# core.hooksPath points at leapwell, which hides every repo-local mechanism, so the first match wins:
#   1. <repo>/.githooks/<hook>
#   2. <repo>/.husky/<hook>          (husky; run with sh because husky does not mark hooks executable)
#   3. <repo>/.pre-commit-config.yaml (pre-commit framework; `pre-commit install` refuses while
#                                      core.hooksPath is set, so it is called directly; missing tool blocks)
#   4. the repo's .git/hooks/<hook>
# A candidate that lives in leapwell's .githooks is skipped to avoid recursion.
chain_repo_hook() {
  hook="$1"; shift
  top="$(git rev-parse --show-toplevel)"
  [ "$(cd "$top" && pwd -P)" = "$LW_ROOT" ] && return 0
  if [ -x "$top/.githooks/$hook" ]; then
    exec "$top/.githooks/$hook" "$@"
  elif [ -f "$top/.husky/$hook" ]; then
    PATH="$top/node_modules/.bin:$PATH" exec sh "$top/.husky/$hook" "$@"
  elif [ -f "$top/.pre-commit-config.yaml" ]; then
    run_pre_commit_framework "$hook" "$@"
  else
    git_dir_hook="$(git rev-parse --git-common-dir)/hooks/$hook"
    [ -x "$git_dir_hook" ] && exec "$git_dir_hook" "$@"
  fi
  return 0
}

# run_pre_commit_framework <hook-name> [args...]: the pre-commit framework's hooks for this stage.
run_pre_commit_framework() {
  hook="$1"; shift
  tool="${LW_PRE_COMMIT:-pre-commit}"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "lw-hooks: this repo uses the pre-commit framework (.pre-commit-config.yaml), but \`pre-commit\` is not" \
      "installed. Install it (pip install pre-commit) and commit again." >&2
    return 1
  fi
  case "$hook" in
    commit-msg) exec "$tool" run --hook-stage commit-msg --commit-msg-filename "$1" ;;
    *) exec "$tool" run --hook-stage "$hook" ;;
  esac
}
