"""Close same-repo issues referenced with close/fix/resolve by a merged PR.

CLI (run by the thin per-repo workflow):
  python3 scripts/sdlc/close_on_merge.py --event "$GITHUB_EVENT_PATH" --repo owner/name [--apply]
Dry-run unless --apply. Needs `gh` authenticated (GH_TOKEN). GitHub only auto-closes
for merges into the default branch, so this covers non-default integration branches.
`refs #N` never closes; cross-repo references (`Closes owner/repo#N`) are ignored.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc.close_parents import GhError, GhRunner, run_gh  # noqa: E402
from scripts.sdlc.patterns import _REF_KEYWORDS  # noqa: E402

# Same keyword set as the PR check; `#N` must follow the keyword directly, which excludes `owner/repo#N`.
_LOCAL_REF_RE = re.compile(rf"\b{_REF_KEYWORDS}\s+#(\d+)\b", re.IGNORECASE)


def local_refs(body: str) -> list[int]:
    """Issue numbers closed by `close|fix|resolve` keywords, in first-seen order, deduplicated."""
    numbers: list[int] = []
    for match in _LOCAL_REF_RE.finditer(body or ""):
        if match.group(1).lower().startswith("ref"):
            continue
        number = int(match.group(match.lastindex))
        if number not in numbers:
            numbers.append(number)
    return numbers


def close_issues(repo: str, pr_number: int, numbers: list[int], apply: bool, gh: GhRunner = run_gh) -> int:
    """Close each issue; returns the count of failures (a failure never stops the rest)."""
    failures = 0
    for number in numbers:
        if not apply:
            print(f"would close #{number}")
            continue
        try:
            gh(["issue", "close", str(number), "--repo", repo, "--comment", f"Closed by merged PR #{pr_number}."])
            print(f"closed #{number}")
        except GhError as exc:
            print(f"could not close #{number}: {exc}")
            failures += 1
    return failures


def main(argv: Optional[list[str]] = None, gh: GhRunner = run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="path to the GitHub event JSON")
    parser.add_argument("--repo", required=True, help="owner/name of the repo the PR belongs to")
    parser.add_argument("--apply", action="store_true", help="actually close (default: dry-run)")
    args = parser.parse_args(argv)
    pull_request = json.loads(Path(args.event).read_text(encoding="utf-8"))["pull_request"]
    if not pull_request.get("merged"):
        print("PR was not merged; nothing to close.")
        return 0
    numbers = local_refs(pull_request.get("body") or "")
    if not numbers:
        print("No close/fix/resolve references found.")
        return 0
    return 1 if close_issues(args.repo, pull_request["number"], numbers, args.apply, gh) else 0


if __name__ == "__main__":
    sys.exit(main())
