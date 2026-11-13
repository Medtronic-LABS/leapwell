"""Set the native GitHub issue type (Epic, Story, Task, Subtask, Bug) of a LeapWell issue.

CLI, dry-run unless --apply:
  python3 scripts/sdlc/issue_types.py --event "$GITHUB_EVENT_PATH" [--apply]
      an intake issue: the type comes from its `type:*` label or title prefix
  python3 -m scripts.sdlc.issue_types --issue OWNER/REPO#n --parent OWNER/REPO#N [--apply]
      a sub-issue: Task under a Story, Bug or Epic; Subtask under a Task

An issue that already has a type is never changed. The mapping lives in scripts.sdlc.patterns.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc.check_issue import detect_type  # noqa: E402
from scripts.sdlc.close_parents import GhError, GhRunner, run_gh  # noqa: E402
from scripts.sdlc.patterns import ISSUE_TYPES  # noqa: E402

TASK = "Task"
SUBTASK = "Subtask"
# A sub-issue of one of these is a Subtask; under anything else it is a Task.
_TASK_LEVEL = frozenset({TASK, SUBTASK})
_REF_RE = re.compile(r"^([\w.-]+/[\w.-]+)#(\d+)$")


def native_type(title: str, labels: list[str]) -> str | None:
    """Issue type for an intake issue, or None when it carries no type label or prefix."""
    kind = detect_type(title, labels)
    return ISSUE_TYPES.get(kind) if kind else None


def child_type(parent_type: str | None) -> str:
    return SUBTASK if parent_type in _TASK_LEVEL else TASK


def current_type(issue: dict) -> str | None:
    """Type name from a REST issue object (`type` is null or {"name": ...})."""
    value = issue.get("type")
    return value.get("name") if isinstance(value, dict) else None


def parse_ref(ref: str) -> tuple[str, int]:
    match = _REF_RE.match(ref.strip())
    if not match:
        raise ValueError(f"expected OWNER/REPO#number, got {ref!r}")
    return match.group(1), int(match.group(2))


def fetch_issue(repo: str, number: int, gh: GhRunner) -> dict:
    return json.loads(gh(["api", f"repos/{repo}/issues/{number}"]))


def set_type(repo: str, number: int, name: str, gh: GhRunner) -> None:
    gh(["api", "-X", "PATCH", f"repos/{repo}/issues/{number}", "-f", f"type={name}"])


def apply_type(repo: str, issue: dict, wanted: str | None, apply: bool, gh: GhRunner) -> None:
    """Set `wanted` on an untyped issue; print what happened (or would happen)."""
    number = issue["number"]
    existing = current_type(issue)
    if existing:
        print(f"#{number}: already {existing}; left alone")
    elif wanted is None:
        print(f"#{number}: no type label or title prefix; left untyped")
    elif apply:
        set_type(repo, number, wanted, gh)
        print(f"#{number}: type set to {wanted}")
    else:
        print(f"#{number}: would set type {wanted} (dry run; pass --apply)")


def from_event(path: str, apply: bool, gh: GhRunner) -> None:
    event = json.loads(Path(path).read_text(encoding="utf-8"))
    issue = event["issue"]
    repo = (event.get("repository") or {}).get("full_name") or os.environ["GITHUB_REPOSITORY"]
    labels = [label["name"] for label in issue.get("labels") or []]
    apply_type(repo, issue, native_type(issue.get("title") or "", labels), apply, gh)


def from_parent(issue_ref: str, parent_ref: str, apply: bool, gh: GhRunner) -> None:
    repo, number = parse_ref(issue_ref)
    parent_repo, parent_number = parse_ref(parent_ref)
    parent = fetch_issue(parent_repo, parent_number, gh)
    apply_type(repo, fetch_issue(repo, number, gh), child_type(current_type(parent)), apply, gh)


def main(argv: list[str] | None = None, gh: GhRunner = run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--event", help="path to the GitHub issues event JSON")
    target.add_argument("--issue", help="sub-issue as OWNER/REPO#number (needs --parent)")
    parser.add_argument("--parent", help="parent issue as OWNER/REPO#number")
    parser.add_argument("--apply", action="store_true", help="actually set the type (default is dry run)")
    args = parser.parse_args(argv)
    if args.issue and not args.parent:
        parser.error("--issue needs --parent")
    try:
        if args.event:
            from_event(args.event, args.apply, gh)
        else:
            from_parent(args.issue, args.parent, args.apply, gh)
    except (GhError, ValueError, KeyError, OSError) as exc:
        print(f"issue-types failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
