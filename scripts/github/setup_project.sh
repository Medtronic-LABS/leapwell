#!/usr/bin/env bash
# Configure Project #4 for Scrum: repo links, issue types, Priority / Sprint / Story Points fields,
# the five planning views and the project README. Dry-run by default. Process: docs/process/BOARD.md.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# Overridable from the environment, like OWNER / REPO / PROJECT in lib.sh.
SPRINT_FIELD="${SPRINT_FIELD:-Sprint}"
SPRINT_START="${SPRINT_START:-2026-11-16}"   # a Monday
SPRINT_DAYS="${SPRINT_DAYS:-14}"
SPRINT_COUNT="${SPRINT_COUNT:-12}"
POINTS_FIELD="Story Points"
LEGACY_POINTS_FIELD="Estimate"               # unused number field from the project template
BOARD_DOC="https://github.com/$OWNER/$REPO/blob/main/docs/process/BOARD.md"

# name|colour|description of the issue types added to the org's Task, Bug and Feature.
ISSUE_TYPES=(
  "Epic|PURPLE|A large goal that groups several stories and spans sprints"
  "Story|GREEN|A user-facing feature request, delivered within a sprint"
  "Subtask|GRAY|A piece of a Task"
)
# name|layout|filter. Grouping, sorting, sums and slices are UI-only (printed below).
VIEWS=(
  "Product Backlog|TABLE_LAYOUT|is:open"
  "Sprint Planning|TABLE_LAYOUT|is:open -type:Epic"
  "Active Sprint|BOARD_LAYOUT|sprint:@current -type:Epic"
  "Release Roadmap|ROADMAP_LAYOUT|type:Epic"
  "My Work|TABLE_LAYOUT|assignee:@me is:open"
)

usage() {
  cat <<USAGE
Usage: scripts/github/setup_project.sh [--apply] [--help]

Configures project #$PROJECT of $OWNER for Scrum (see docs/process/BOARD.md):
  Link          links $OWNER/$REPO and every code repo in repos.json to the project
  Issue types   Epic, Story, Subtask (org-wide; created only if missing)
  Priority      single-select P0, P1, P2, P3 (created only if missing)
  $SPRINT_FIELD        iteration field, $SPRINT_COUNT sprints of $SPRINT_DAYS days from $SPRINT_START (only if missing)
  $POINTS_FIELD  number field; the unused '$LEGACY_POINTS_FIELD' field is renamed (only if missing)
  Views         Product Backlog, Sprint Planning, Active Sprint, Release Roadmap, My Work
                (created only if missing; existing views are never changed or deleted)
  README        short description and a pointer to the board guide
  Status        NOT touched by this script: replacing the option list via the API can
                wipe item values. Add Triage and QA in the UI (steps printed).
Nothing existing is overwritten or deleted. Default is a dry-run that only prints the gh commands.
USAGE
}

parse_common_flags usage "$@"
reject_unknown_args
banner

# --- current state (read-only; skipped in dry-run so no gh call is made there) -----------------
STATE=""
if [ "$APPLY" -eq 1 ]; then
  # shellcheck disable=SC2016  # $org / $number are GraphQL variables
  STATE="$(gh api graphql -F org="$OWNER" -F number="$PROJECT" -f query='
    query($org: String!, $number: Int!) {
      organization(login: $org) {
        id
        issueTypes(first: 50) { nodes { name } }
        projectV2(number: $number) {
          id
          readme
          fields(first: 50) { nodes { ... on ProjectV2FieldCommon { id name } } }
          views(first: 50) { nodes { name } }
          repositories(first: 50) { nodes { nameWithOwner } }
        }
      }
    }' --jq '.data.organization as $o
      | "org\t\($o.id)", "project\t\($o.projectV2.id)",
        (if ($o.projectV2.readme // "") == "" then empty else "readme\tset" end),
        ($o.issueTypes.nodes[] | "type\t\(.name)"),
        ($o.projectV2.fields.nodes[] | "field\t\(.name)\t\(.id)"),
        ($o.projectV2.views.nodes[] | "view\t\(.name)"),
        ($o.projectV2.repositories.nodes[] | "repo\t\(.nameWithOwner)")')"
fi

# state_has KIND NAME: true when the object already exists (always false in dry-run).
state_has() {
  printf '%s\n' "$STATE" | awk -F '\t' -v kind="$1" -v name="$2" \
    '$1 == kind && $2 == name { found = 1 } END { exit !found }'
}

# state_id KIND [NAME]: the node id, or a readable placeholder in dry-run.
state_id() {
  local found
  found="$(printf '%s\n' "$STATE" | awk -F '\t' -v kind="$1" -v name="${2:-}" \
    '$1 == kind && (name == "" || $2 == name) { print $NF; exit }')"
  printf '%s' "${found:-<${2:-$1}-id>}"
}

ORG_ID="$(state_id org)"
PROJECT_ID="$(state_id project)"

# --- repo links --------------------------------------------------------------------------------
echo
echo "-- Link the tracker and the code repos to project #$PROJECT --"
link_repo() {
  if state_has repo "$1"; then
    echo "$1 is already linked; leaving it alone."
  else
    run gh project link "$PROJECT" --owner "$OWNER" --repo "$1"
  fi
}
link_repo "$OWNER/$REPO"
while read -r _key name _branch; do
  link_repo "$OWNER/$name"
done < <(manifest_repos)

# --- issue types (org-wide) --------------------------------------------------------------------
echo
echo "-- Issue types (org-wide: they appear in every $OWNER repo) --"
for entry in "${ISSUE_TYPES[@]}"; do
  IFS='|' read -r type_name type_color type_description <<<"$entry"
  if state_has type "$type_name"; then
    echo "Issue type $type_name already exists; leaving it alone."
  else
    # shellcheck disable=SC2016
    run gh api graphql -f owner="$ORG_ID" -f name="$type_name" -f description="$type_description" \
      -f color="$type_color" -f query='
      mutation($owner: ID!, $name: String!, $description: String!, $color: IssueTypeColor!) {
        createIssueType(input: {ownerId: $owner, name: $name, description: $description,
                                color: $color, isEnabled: true}) { issueType { id name } }
      }'
  fi
done
echo "  If GitHub refuses (needs an org owner and the admin:org scope): gh auth refresh -s admin:org,"
echo "  or create the three types in the UI: Organization -> Settings -> Planning -> Issue types."

# --- fields ------------------------------------------------------------------------------------
ensure_select_field() {
  local name="$1" options="$2"
  if state_has field "$name"; then
    echo "$name field already exists; leaving it alone."
  else
    run gh project field-create "$PROJECT" --owner "$OWNER" --name "$name" \
      --data-type SINGLE_SELECT --single-select-options "$options"
  fi
}

echo
echo "-- Priority --"
ensure_select_field Priority "P0,P1,P2,P3"

# JSON request body that creates the iteration field with titled, back-to-back sprints.
sprint_request() {
  python3 - "$PROJECT_ID" "$SPRINT_FIELD" "$SPRINT_START" "$SPRINT_DAYS" "$SPRINT_COUNT" <<'PY'
import datetime
import json
import sys

project_id, name, start, days, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
first = datetime.date.fromisoformat(start)
iterations = [
    {"title": f"{name} {index + 1:02d}", "startDate": (first + datetime.timedelta(days=index * days)).isoformat(), "duration": days}
    for index in range(count)
]
query = (
    "mutation($input: CreateProjectV2FieldInput!) { createProjectV2Field(input: $input) "
    "{ projectV2Field { ... on ProjectV2IterationField { id name } } } }"
)
variables = {
    "input": {
        "projectId": project_id,
        "dataType": "ITERATION",
        "name": name,
        "iterationConfiguration": {"startDate": start, "duration": days, "iterations": iterations},
    }
}
print(json.dumps({"query": query, "variables": variables}, indent=2))
PY
}

echo
echo "-- $SPRINT_FIELD ($SPRINT_COUNT sprints of $SPRINT_DAYS days from $SPRINT_START) --"
if state_has field "$SPRINT_FIELD"; then
  echo "$SPRINT_FIELD field already exists; leaving it alone (add sprints in the UI)."
else
  run_stdin "$(sprint_request)" gh api graphql --input -
fi

echo
echo "-- $POINTS_FIELD --"
if state_has field "$POINTS_FIELD"; then
  echo "$POINTS_FIELD field already exists; leaving it alone."
elif [ "$APPLY" -eq 0 ] || state_has field "$LEGACY_POINTS_FIELD"; then
  # Rename only: no option list is sent, so no item value can be lost.
  # shellcheck disable=SC2016
  run gh api graphql -f field="$(state_id field "$LEGACY_POINTS_FIELD")" -f name="$POINTS_FIELD" -f query='
    mutation($field: ID!, $name: String!) {
      updateProjectV2Field(input: {fieldId: $field, name: $name}) {
        projectV2Field { ... on ProjectV2Field { id name } }
      }
    }'
else
  run gh project field-create "$PROJECT" --owner "$OWNER" --name "$POINTS_FIELD" --data-type NUMBER
fi

# --- views -------------------------------------------------------------------------------------
# shellcheck disable=SC2016
CREATE_VIEW='mutation($project: ID!, $name: String!, $layout: ProjectV2ViewLayout!) {
  createProjectV2View(input: {projectId: $project, name: $name, layout: $layout}) { projectV2View { id } }
}'
# shellcheck disable=SC2016
FILTER_VIEW='mutation($view: ID!, $filter: String!) {
  updateProjectV2View(input: {viewId: $view, filter: $filter}) { projectV2View { id name filter } }
}'

echo
echo "-- Views (new ones only; existing views are never changed or deleted) --"
for entry in "${VIEWS[@]}"; do
  IFS='|' read -r view_name view_layout view_filter <<<"$entry"
  if state_has view "$view_name"; then
    echo "View '$view_name' already exists; leaving it alone."
    continue
  fi
  view_id="<$view_name-view-id>"
  if [ "$APPLY" -eq 1 ]; then
    echo "+ create view '$view_name' ($view_layout)"
    view_id="$(gh api graphql -f project="$PROJECT_ID" -f name="$view_name" -f layout="$view_layout" \
      -f query="$CREATE_VIEW" --jq '.data.createProjectV2View.projectV2View.id')"
  else
    run gh api graphql -f project="$PROJECT_ID" -f name="$view_name" -f layout="$view_layout" -f query="$CREATE_VIEW"
  fi
  run gh api graphql -f view="$view_id" -f filter="$view_filter" -f query="$FILTER_VIEW"
done

# --- README ------------------------------------------------------------------------------------
echo
echo "-- Project description and README --"
README="LeapWell board: Epic > Story > Task > Subtask, plus Bug. Two-week sprints.
Hierarchy, views, sprint planning checklist and hygiene filters: $BOARD_DOC"
if state_has readme set; then
  echo "The project already has a README; leaving it alone."
else
  # shellcheck disable=SC2016
  run gh api graphql -f project="$PROJECT_ID" -f readme="$README" \
    -f description="LeapWell Scrum board: backlog, sprints and roadmap" -f query='
    mutation($project: ID!, $readme: String!, $description: String!) {
      updateProjectV2(input: {projectId: $project, readme: $readme, shortDescription: $description}) {
        projectV2 { id }
      }
    }'
fi

# --- UI-only steps -----------------------------------------------------------------------------
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
echo "    (the Free plan allows one Auto-add workflow; code-repo work arrives through"
echo "     'Auto-add sub-issues to project', which must stay enabled)"

echo
echo "-- View layout (UI only: open each view -> View menu) --"
echo "  * Product Backlog   show sub-issue hierarchy; sort by Priority"
echo "  * Sprint Planning   group by $SPRINT_FIELD; field sum: $POINTS_FIELD; slice by Assignees"
echo "  * Active Sprint     column field: Status; field sum: $POINTS_FIELD; slice by Type"
echo "  * Release Roadmap   dates: Start date -> Target date; markers: $SPRINT_FIELD, Milestone"
echo "  * My Work           group by Status"
echo "  Insights charts and the full checklist: docs/process/ADMIN_SETUP.md section 3."
