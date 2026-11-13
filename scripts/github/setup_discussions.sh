#!/usr/bin/env bash
# Check Discussions is enabled and which categories exist. Dry-run by default.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
  cat <<USAGE
Usage: scripts/github/setup_discussions.sh [--apply] [--help]

For $OWNER/$REPO:
  - checks Discussions is enabled (enables it with --apply)
  - lists existing categories via GraphQL and reports which of the wanted ones are missing
Categories cannot be created through the API: the UI steps are printed.
Default is a dry-run that prints the commands and the UI steps without calling gh.
USAGE
}

parse_common_flags usage "$@"
reject_unknown_args
banner

WANTED=("Ideas" "Field feedback" "Partner requests" "Q&A" "Announcements")
FORMS_NOTE="Discussion form files in .github/DISCUSSION_TEMPLATE/ are named by category slug: ideas, field-feedback, partner-requests."

print_ui_steps() {
  echo "UI steps (Repo -> Discussions -> pencil icon next to Categories):"
  local name
  for name in "$@"; do
    echo "  * New category '$name'"
  done
  echo "  Use format 'Open-ended discussion' for Ideas, Field feedback and Partner requests,"
  echo "  'Question / Answer' for Q&A and 'Announcement' for Announcements."
  echo "$FORMS_NOTE"
}

ENABLED_QUERY="repos/$OWNER/$REPO"
CATEGORIES_QUERY='query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { discussionCategories(first: 25) { nodes { name } } } }'

echo
echo "-- Is Discussions enabled? --"
if [ "$APPLY" -eq 1 ]; then
  has="$(gh api "$ENABLED_QUERY" --jq .has_discussions)"
  if [ "$has" = "true" ]; then
    echo "Discussions is enabled."
  else
    run gh repo edit "$OWNER/$REPO" --enable-discussions
  fi
else
  echo "[dry-run] $(quote_cmd gh api "$ENABLED_QUERY" --jq .has_discussions)"
  echo "[dry-run] if false: $(quote_cmd gh repo edit "$OWNER/$REPO" --enable-discussions)"
fi

echo
echo "-- Existing categories --"
if [ "$APPLY" -eq 1 ]; then
  existing="$(gh api graphql -f query="$CATEGORIES_QUERY" -f owner="$OWNER" -f name="$REPO" \
    --jq '.data.repository.discussionCategories.nodes[].name')"
  missing=()
  for name in "${WANTED[@]}"; do
    if printf '%s\n' "$existing" | grep -qxF "$name"; then
      echo "  present: $name"
    else
      echo "  MISSING: $name"
      missing+=("$name")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo
    print_ui_steps "${missing[@]}"
  fi
else
  echo "[dry-run] $(quote_cmd gh api graphql -f "query=$CATEGORIES_QUERY" -f "owner=$OWNER" -f "name=$REPO")"
  echo
  print_ui_steps "${WANTED[@]}"
fi
