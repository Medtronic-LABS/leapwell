#!/usr/bin/env bash
# Link leapwell to Project #4 and ensure its Priority and Type fields. Dry-run by default.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
  cat <<USAGE
Usage: scripts/github/setup_project.sh [--apply] [--help]

Configures project #$PROJECT of $OWNER:
  Link      links $OWNER/$REPO to the project
  Priority  single-select P0, P1, P2, P3 (created only if missing)
  Type      single-select Bug, Feature, Task, Release (created only if missing)
  Status    NOT touched by this script: replacing the option list via the API can
            wipe item values. Add Triage and QA in the UI (steps printed).
Default is a dry-run that only prints the gh commands.
USAGE
}

parse_common_flags usage "$@"
reject_unknown_args
banner

# Read-only lookup; skipped in dry-run so no gh call is made there.
field_exists() {
  [ "$APPLY" -eq 1 ] || return 1
  local names
  names="$(gh project field-list "$PROJECT" --owner "$OWNER" --format json \
    --jq ".fields[] | .name")"
  printf '%s\n' "$names" | grep -Fx -- "$1" >/dev/null
}

ensure_select_field() {
  local name="$1" options="$2"
  if field_exists "$name"; then
    echo "$name field already exists; leaving it alone."
  else
    run gh project field-create "$PROJECT" --owner "$OWNER" --name "$name" \
      --data-type SINGLE_SELECT --single-select-options "$options"
  fi
}

echo
echo "-- Link $OWNER/$REPO to project #$PROJECT --"
run gh project link "$PROJECT" --owner "$OWNER" --repo "$OWNER/$REPO"

echo
echo "-- Priority --"
ensure_select_field Priority "P0,P1,P2,P3"

echo
echo "-- Type --"
ensure_select_field Type "Bug,Feature,Task,Release"

echo
echo "-- Status (UI only; this script never edits Status) --"
echo "  The API replaces the whole option list and can wipe item Status values."
echo "  In the UI: Project -> Settings -> Status field ->"
echo "    add 'Triage' and drag it to the top;"
echo "    add 'QA' and place it between 'In review' and 'Done'."
echo "  Adding options in the UI keeps existing item values."
echo "  Target order: Triage, Backlog, Ready, In progress, In review, QA, Done."

echo
echo "-- Built-in workflows to enable manually (UI only: Project -> Workflows) --"
echo "  * Item added to project   -> set Status = Triage"
echo "  * Item closed             -> set Status = Done"
echo "  * Pull request merged     -> set Status = Done"
echo "  * Item reopened           -> set Status = In progress"
echo "  * Auto-add to project     -> filter: repo:$OWNER/$REPO is:issue"
echo "    (add a second Auto-add workflow per code repo to show sub-issues; the Repository"
echo "     field separates the two levels)"
