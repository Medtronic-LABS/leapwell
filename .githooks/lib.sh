# Shared by commit-msg and pre-commit (sourced). Resolves leapwell's root from the
# hook's own path, so it works from any repos/<x> clone whose core.hooksPath points here.
LW_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

# chain_repo_hook <hook-name> [args...]: run the repo's own hook (stdin passed through).
# Preference: <repo>/.githooks/<hook>, else the repo's .git/hooks (pre-commit framework; core.hooksPath hides it from --git-path).
# A candidate that lives in leapwell's .githooks is skipped to avoid recursion.
chain_repo_hook() {
  hook="$1"; shift
  top="$(git rev-parse --show-toplevel)"
  for candidate in "$top/.githooks/$hook" "$(git rev-parse --git-common-dir)/hooks/$hook"; do
    [ -x "$candidate" ] || continue
    cand_dir="$(cd "$(dirname "$candidate")" && pwd -P)"
    [ "$cand_dir" = "$LW_ROOT/.githooks" ] && continue
    exec "$candidate" "$@"
  done
  return 0
}
