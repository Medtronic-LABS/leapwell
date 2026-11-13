"""Housekeeping for the LeapWell project board (org Project from repos.json).

CLI, dry-run unless --apply:
  python3 -m scripts.sdlc.project_board sprint-sync [--apply]
      GitHub does not copy a parent's Sprint to its sub-issues. This fills an empty Sprint on
      every open issue from its parent (Story -> Task -> Subtask) and lists children whose
      Sprint differs from the parent's. It never overwrites a Sprint and never touches closed items.
  python3 -m scripts.sdlc.project_board reconcile [--apply]
      Adds open issues of the tracker and the code repos that are missing from the project, and
      sets a missing issue type: tracker issues from their `type:*` label, sub-issues from their parent.

Run by a person at sprint planning; never scheduled. Needs `gh` with the `project` scope.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc import repos  # noqa: E402
from scripts.sdlc.close_parents import GhError, GhRunner, _json_pages, run_gh  # noqa: E402
from scripts.sdlc.issue_types import child_type, current_type, native_type, set_type  # noqa: E402

SPRINT_FIELD = "Sprint"
OPEN = "OPEN"
DRY_RUN_HINT = "(dry run; pass --apply)"

Sprint = tuple[str, str]  # (iteration id, title)

_BOARD_QUERY = """
query($org: String!, $number: Int!, $endCursor: String) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      fields(first: 50) { nodes { ... on ProjectV2IterationField { id name } } }
      items(first: 100, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          sprint: fieldValueByName(name: "SPRINT_FIELD") {
            ... on ProjectV2ItemFieldIterationValue { iterationId title }
          }
          content {
            __typename
            ... on Issue {
              id number state
              repository { nameWithOwner }
              issueType { name }
              parent { id }
            }
          }
        }
      }
    }
  }
}
""".replace("SPRINT_FIELD", SPRINT_FIELD)

_SET_SPRINT_MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: {iterationId: $iterationId}
  }) { projectV2Item { id } }
}
"""


@dataclass(frozen=True)
class Item:
    """One issue on the board."""

    item_id: str
    content_id: str
    repo: str
    number: int
    state: str
    issue_type: str | None
    parent_id: str | None
    sprint: Sprint | None

    @property
    def is_open(self) -> bool:
        return self.state == OPEN

    @property
    def label(self) -> str:
        return f"{self.repo.split('/', 1)[-1]}#{self.number}"


@dataclass(frozen=True)
class Board:
    project_id: str
    sprint_field_id: str | None
    items: tuple[Item, ...]


@dataclass(frozen=True)
class SprintChange:
    item: Item
    sprint: Sprint


def _item(node: dict) -> Item | None:
    """An Item for an issue node; None for drafts, pull requests and unreadable content."""
    content = node.get("content") or {}
    if content.get("__typename") != "Issue":
        return None
    sprint = node.get("sprint") or {}
    return Item(
        item_id=node["id"],
        content_id=content["id"],
        repo=content["repository"]["nameWithOwner"],
        number=content["number"],
        state=content["state"],
        issue_type=(content.get("issueType") or {}).get("name"),
        parent_id=(content.get("parent") or {}).get("id"),
        sprint=(sprint["iterationId"], sprint["title"]) if sprint.get("iterationId") else None,
    )


def _sprint_field_id(project: dict) -> str | None:
    """Id of the Sprint iteration field, or None. (`field(name:)` errors on a missing field, so list them.)"""
    for field in (project.get("fields") or {}).get("nodes") or []:
        if field and field.get("name") == SPRINT_FIELD:
            return field["id"]
    return None


def load_board(org: str, number: int, gh: GhRunner) -> Board:
    out = gh(
        ["api", "graphql", "--paginate", "-f", f"query={_BOARD_QUERY}", "-F", f"org={org}", "-F", f"number={number}"]
    )
    project_id, field_id, items = "", None, []
    for page in _json_pages(out):
        project = page["data"]["organization"]["projectV2"]
        project_id = project["id"]
        field_id = _sprint_field_id(project)
        items.extend(item for item in map(_item, project["items"]["nodes"]) if item)
    return Board(project_id=project_id, sprint_field_id=field_id, items=tuple(items))


def plan_sprints(items: list[Item] | tuple[Item, ...]) -> list[SprintChange]:
    """Open issues with no Sprint whose parent has one, cascading down the hierarchy."""
    sprint_of = {item.content_id: item.sprint for item in items}
    changes: list[SprintChange] = []
    pending = [item for item in items if item.is_open and item.sprint is None and item.parent_id]
    progressed = True
    while progressed:
        progressed = False
        for item in list(pending):
            inherited = sprint_of.get(item.parent_id)
            if inherited:
                sprint_of[item.content_id] = inherited
                changes.append(SprintChange(item, inherited))
                pending.remove(item)
                progressed = True
    return changes


def sprint_mismatches(items: list[Item] | tuple[Item, ...]) -> list[Item]:
    """Open issues whose Sprint differs from their parent's (reported, never changed)."""
    sprint_of = {item.content_id: item.sprint for item in items}
    return [
        item
        for item in items
        if item.is_open and item.sprint and sprint_of.get(item.parent_id) and sprint_of[item.parent_id] != item.sprint
    ]


def sprint_sync(board: Board, apply: bool, gh: GhRunner) -> int:
    """Return the number of failed writes."""
    if not board.sprint_field_id:
        raise ValueError(f"the project has no {SPRINT_FIELD} field; run scripts/github/setup_project.sh first")
    failed = 0
    changes = plan_sprints(board.items)
    for change in changes:
        iteration_id, title = change.sprint
        if not apply:
            print(f"{change.item.label}: would set {title} {DRY_RUN_HINT}")
            continue
        try:
            gh(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"query={_SET_SPRINT_MUTATION}",
                    "-f",
                    f"projectId={board.project_id}",
                    "-f",
                    f"itemId={change.item.item_id}",
                    "-f",
                    f"fieldId={board.sprint_field_id}",
                    "-f",
                    f"iterationId={iteration_id}",
                ]
            )
            print(f"{change.item.label}: set {title}")
        except GhError as exc:
            failed += 1
            print(f"{change.item.label}: could not set {title}: {exc}", file=sys.stderr)
    for item in sprint_mismatches(board.items):
        print(f"{item.label}: Sprint {item.sprint[1]} differs from its parent's (not changed)")
    if not changes:
        print("Every open sub-issue of a planned item already has a Sprint.")
    return failed


def _open_issues(slug: str, gh: GhRunner) -> list[dict]:
    out = gh(["api", "--paginate", f"repos/{slug}/issues?state=open&per_page=100"])
    return [issue for issue in _json_pages(out) if "pull_request" not in issue]


def _set_missing_type(slug: str, label: str, number: int, wanted: str, apply: bool, gh: GhRunner) -> int:
    if not apply:
        print(f"{label}: would set type {wanted} {DRY_RUN_HINT}")
        return 0
    try:
        set_type(slug, number, wanted, gh)
        print(f"{label}: type set to {wanted}")
        return 0
    except GhError as exc:
        print(f"{label}: could not set type {wanted}: {exc}", file=sys.stderr)
        return 1


def reconcile(manifest: repos.Manifest, board: Board, apply: bool, gh: GhRunner) -> int:
    """Return the number of failures (unreadable repos and failed writes)."""
    failed = 0
    on_board = {item.content_id for item in board.items}
    type_of = {item.content_id: item.issue_type for item in board.items}
    slugs = [manifest.tracker_slug] + [f"{manifest.org}/{repo.name}" for repo in manifest.repos]
    for slug in slugs:
        name = slug.split("/", 1)[-1]
        try:
            issues = _open_issues(slug, gh)
        except (GhError, ValueError) as exc:
            failed += 1
            print(f"{name}: could not list issues: {exc}", file=sys.stderr)
            continue
        for issue in issues:
            label = f"{name}#{issue['number']}"
            if issue["node_id"] not in on_board:
                failed += _add_to_project(manifest, label, issue["html_url"], apply, gh)
            wanted = native_type(issue.get("title") or "", [entry["name"] for entry in issue.get("labels") or []])
            if slug == manifest.tracker_slug and wanted and not current_type(issue):
                failed += _set_missing_type(slug, label, issue["number"], wanted, apply, gh)
                type_of[issue["node_id"]] = wanted  # so its sub-issues are typed in the same run
    for item in board.items:
        # A sub-issue is typed only from a parent whose own type is known; nothing is guessed.
        parent_type = type_of.get(item.parent_id)
        if item.is_open and not type_of.get(item.content_id) and parent_type:
            wanted = child_type(parent_type)
            failed += _set_missing_type(item.repo, item.label, item.number, wanted, apply, gh)
            type_of[item.content_id] = wanted
    return failed


def _add_to_project(manifest: repos.Manifest, label: str, url: str, apply: bool, gh: GhRunner) -> int:
    if not apply:
        print(f"{label}: would add to the project {DRY_RUN_HINT}")
        return 0
    try:
        gh(["project", "item-add", str(manifest.project), "--owner", manifest.org, "--url", url])
        print(f"{label}: added to the project")
        return 0
    except GhError as exc:
        print(f"{label}: could not add to the project: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None, gh: GhRunner = run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("sprint-sync", "reconcile"))
    parser.add_argument("--apply", action="store_true", help="actually write (default is dry run)")
    args = parser.parse_args(argv)
    try:
        manifest = repos.load()
        board = load_board(manifest.org, manifest.project, gh)
        if args.command == "sprint-sync":
            failed = sprint_sync(board, args.apply, gh)
        else:
            failed = reconcile(manifest, board, args.apply, gh)
    except (GhError, ValueError, KeyError, OSError) as exc:
        print(f"project-board failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if failed:
        print(f"{failed} change(s) failed; see the messages above.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
