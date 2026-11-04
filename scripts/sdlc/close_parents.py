"""Close routed leapwell parent issues once every sub-issue is closed.

CLI: python3 scripts/sdlc/close_parents.py [--repo Medtronic-LABS/leapwell] [--apply]
Dry-run unless --apply. Needs `gh` authenticated; the workflow exports GH_TOKEN
(from LEAPWELL_BOT_TOKEN, falling back to GITHUB_TOKEN).

An item is closed only if it is open, labelled `status:routed`, has at least one
sub-issue, every sub-issue is readable, and every sub-issue is closed (any
state_reason, so "not planned" counts).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc import repos  # noqa: E402

ROUTED_LABEL = "status:routed"

GhRunner = Callable[[list[str]], str]


class GhError(RuntimeError):
    """A gh call failed; the message carries no response content."""


def run_gh(args: list[str]) -> str:
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GhError(f"gh {args[0]} could not run: {type(exc).__name__}") from exc
    if done.returncode != 0:
        raise GhError(f"gh {' '.join(args[:2])} failed (exit {done.returncode})")
    return done.stdout


def decide(parent: dict, subs: list[dict], unreadable: int = 0) -> bool:
    """True only when the parent is safe to close (see module docstring)."""
    labels = {label.get("name") if isinstance(label, dict) else label for label in parent.get("labels", [])}
    return (
        parent.get("state") == "open"
        and ROUTED_LABEL in labels
        and len(subs) >= 1
        and unreadable == 0
        and all(sub.get("state") == "closed" for sub in subs)
    )


def _json_pages(text: str) -> list[dict]:
    """`gh api --paginate` prints one JSON array per page, concatenated; flatten them."""
    decoder = json.JSONDecoder()
    items: list[dict] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        page, index = decoder.raw_decode(text, index)
        items.extend(page if isinstance(page, list) else [page])
    return items


def list_routed(repo: str, gh: GhRunner) -> list[dict]:
    out = gh(["api", "--paginate", f"repos/{repo}/issues?state=open&labels={ROUTED_LABEL}&per_page=100"])
    return [issue for issue in _json_pages(out) if "pull_request" not in issue]


def fetch_subs(repo: str, number: int, gh: GhRunner) -> Optional[list[dict]]:
    """Sub-issues of an issue, or None when they cannot be read (fail safe)."""
    try:
        return _json_pages(gh(["api", "--paginate", f"repos/{repo}/issues/{number}/sub_issues?per_page=100"]))
    except (GhError, ValueError):
        return None


def close_comment(subs: list[dict]) -> str:
    urls = "\n".join(f"- {sub.get('html_url', '')}" for sub in subs)
    return f"All sub-issues are closed, closing this parent:\n\n{urls}"


def close_issue(repo: str, number: int, subs: list[dict], gh: GhRunner) -> None:
    gh(["api", "-X", "POST", f"repos/{repo}/issues/{number}/comments", "-f", f"body={close_comment(subs)}"])
    gh(["api", "-X", "PATCH", f"repos/{repo}/issues/{number}", "-f", "state=closed", "-f", "state_reason=completed"])


def process(repo: str, apply: bool, gh: GhRunner = run_gh) -> list[int]:
    """Return the issue numbers closed (or that would be closed in a dry run)."""
    closable: list[int] = []
    for parent in list_routed(repo, gh):
        number = parent["number"]
        subs = fetch_subs(repo, number, gh)
        unreadable = 1 if subs is None else 0
        subs = subs or []
        if not decide(parent, subs, unreadable):
            reason = "sub-issues unreadable" if unreadable else "not ready"
            print(f"#{number}: keep open ({reason})")
            continue
        closable.append(number)
        if apply:
            close_issue(repo, number, subs, gh)
            print(f"#{number}: closed")
        else:
            print(f"#{number}: would close (dry run; pass --apply)")
    return closable


def main(argv: Optional[list[str]] = None, gh: GhRunner = run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=None, help="owner/name (default: the manifest tracker)")
    parser.add_argument("--apply", action="store_true", help="actually comment and close (default is dry run)")
    args = parser.parse_args(argv)
    repo = args.repo or repos.load().tracker_slug
    try:
        process(repo, args.apply, gh)
    except GhError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
