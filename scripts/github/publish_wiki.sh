#!/usr/bin/env bash
# Seed the GitHub Wiki from wiki/*.md. Dry-run by default (clones, commits locally, never pushes).
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
  cat <<USAGE
Usage: scripts/github/publish_wiki.sh [--force] [--apply] [--help]

Clones the wiki repo of $OWNER/$REPO to a temp dir, copies wiki/*.md into it, commits,
and pushes only with --apply.
  --force   overwrite a wiki that already has content (default: refuse)
Wiki remote: \${WIKI_URL:-https://github.com/$OWNER/$REPO.wiki.git}
GitHub creates the wiki repo with the first page: create it in the UI first.
USAGE
}

parse_common_flags usage "$@"
FORCE=0
for arg in ${REST[@]+"${REST[@]}"}; do
  case "$arg" in
    --force) FORCE=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done
banner

WIKI_URL="${WIKI_URL:-https://github.com/$OWNER/$REPO.wiki.git}"
SOURCE_DIR="${WIKI_SOURCE_DIR:-$REPO_ROOT/wiki}"

shopt -s nullglob
pages=("$SOURCE_DIR"/*.md)
shopt -u nullglob
if [ "${#pages[@]}" -eq 0 ]; then
  echo "No wiki pages found: put Markdown files in $SOURCE_DIR (wiki/ in the repo) and re-run." >&2
  exit 1
fi

if ! remote_err="$(git ls-remote "$WIKI_URL" 2>&1 >/dev/null)"; then
  echo "The wiki repo does not exist yet or is not accessible ($WIKI_URL)."
  echo "git said: $remote_err"
  echo "Create the first wiki page in the UI (Wiki -> Create the first page), then re-run"
  [ "$APPLY" -eq 1 ] && exit 1
  exit 0
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git clone --quiet "$WIKI_URL" "$work/wiki" 2>/dev/null

# "Non-empty" means anything beyond .git, except a lone auto-created placeholder Home page is still content.
existing="$(find "$work/wiki" -mindepth 1 -maxdepth 1 -not -name .git | wc -l | tr -d ' ')"
if [ "$existing" -gt 0 ] && [ "$FORCE" -ne 1 ]; then
  echo "Refusing: the wiki already has $existing item(s). The live wiki is the source of truth after seeding." >&2
  echo "Re-run with --force to overwrite pages with the same names." >&2
  exit 1
fi

cp "${pages[@]}" "$work/wiki/"
cd "$work/wiki"
git add -A
if git diff --cached --quiet; then
  echo "Wiki already matches wiki/; nothing to publish."
  exit 0
fi
git -c user.name="${GIT_AUTHOR_NAME:-leapwell-bot}" -c user.email="${GIT_AUTHOR_EMAIL:-noreply@users.noreply.github.com}" \
  commit --quiet -m "docs(wiki): seed from wiki/ in the repo"
echo "Prepared a commit with ${#pages[@]} page(s):"
git diff --stat HEAD~1 HEAD 2>/dev/null || git show --stat --oneline HEAD
run git push origin HEAD
