"""Render leapwell's thin per-repo layer into the workspace clones under `repos/<name>`.

CLI: python3 scripts/sync/sync_repos.py (--repo KEY | --all) [--ref REF] [--apply] [--workspace DIR]

Dry-run prints unified diffs and writes nothing. `--apply` commits the change on the local
branch `chore/leapwell-sync` of each clone. Never pushes. A dirty clone is refused.
"""

import argparse
import difflib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc import repos  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "templates" / "repo-layer"
DEFAULT_WORKSPACE = ROOT / "repos"
DEFAULT_REF = "main"
SYNC_BRANCH = "chore/leapwell-sync"

# template -> clone path, rewritten on every sync.
MANAGED_FILES = {
    "pr-check.yml": ".github/workflows/lw-pr-check.yml",
    "secret-scan.yml": ".github/workflows/lw-secret-scan.yml",
    "close-on-merge.yml": ".github/workflows/lw-close-on-merge.yml",
    "pull_request_template.md": ".github/pull_request_template.md",
}
# template -> clone path, written only when the file is absent.
CREATE_ONLY_FILES = {"CODEOWNERS": ".github/CODEOWNERS"}
# (template, clone path, markers, fallback when the file lacks markers); only the marked section is owned by leapwell.
MD_MARKERS = ("<!-- leapwell:begin -->", "<!-- leapwell:end -->")
YML_MARKERS = ("# leapwell:begin", "# leapwell:end")
MARKED_FILES = (
    ("claude-section.md", "CLAUDE.md", MD_MARKERS, "append"),
    ("issue-config.yml", ".github/ISSUE_TEMPLATE/config.yml", YML_MARKERS, "manual"),
)
# GitHub also reads these from the repo root and docs/; a clone's existing copy wins over .github/.
GITHUB_ALT_DIRS = ("", "docs")
ALT_LOCATION_FILES = frozenset({".github/pull_request_template.md", ".github/CODEOWNERS"})
# Written only for repos with lint_rules; the CI toolchain follows from each rule's command.
LINT_TEMPLATE = "lint.yml"
LINT_WORKFLOW = ".github/workflows/lw-lint.yml"
LINT_SETUP_BY_TOOL = {"dart": "flutter.yml", "ruff": "python.yml", "npx": "node.yml"}
RUFF_VERSION = "0.17.3"


@dataclass
class Plan:
    """Outcome of rendering one repo: files to write plus human-readable notes."""

    writes: dict[str, str]
    diffs: list[str]
    notes: list[str]

    @property
    def changed(self) -> bool:
        return bool(self.writes)


class SyncError(RuntimeError):
    """A repo cannot be synced; the message is shown to the operator."""


def render(template: str, repo: repos.Repo, manifest: repos.Manifest, ref: str) -> str:
    values = {
        "org": manifest.org,
        "tracker": manifest.tracker,
        "repo": repo.name,
        "integration_branch": repo.integration_branch,
        "leapwell_ref": ref,
        "ruff_version": RUFF_VERSION,
    }
    for name, value in values.items():
        template = template.replace("{{" + name + "}}", value)
    return template


def lint_setup(repo: repos.Repo) -> str:
    """CI steps installing the tools the repo's lint_rules run, in first-use order."""
    snippets: list[str] = []
    for rule in repo.lint_rules:
        tool = rule.run.split()[0]
        if tool not in LINT_SETUP_BY_TOOL:
            raise SyncError(f"no CI setup for lint tool {tool!r}; add one to LINT_SETUP_BY_TOOL")
        snippet = LINT_SETUP_BY_TOOL[tool]
        if snippet not in snippets:
            snippets.append(snippet)
    return "".join(_template(f"lint-setup/{name}") for name in snippets)


def _marker_re(markers: tuple[str, str]) -> re.Pattern[str]:
    begin, end = (re.escape(m) for m in markers)
    return re.compile(rf"^[ \t]*{begin}[ \t]*\n.*?^[ \t]*{end}[ \t]*$", re.DOTALL | re.MULTILINE)


def replace_marked(existing: str, block: str, markers: tuple[str, str]) -> str | None:
    """Swap the marked section for `block`; None when the markers are absent. Other bytes are untouched."""
    pattern = _marker_re(markers)
    if not pattern.search(existing):
        return None
    return pattern.sub(lambda _: block.rstrip("\n"), existing, count=1)


def _diff(path: str, old: str | None, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            (old or "").splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="/dev/null" if old is None else f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def _read(clone: Path, rel: str) -> str | None:
    path = clone / rel
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _existing_spelling(clone: Path, rel: str) -> str | None:
    """`rel` as the clone spells it (letter case can differ), or None when no such file exists."""
    target = Path(rel)
    parent = clone / target.parent
    if not parent.is_dir():
        return None
    for entry in sorted(parent.iterdir()):
        if entry.name.lower() == target.name.lower() and entry.is_file():
            return str(target.parent / entry.name)
    return None


def resolve_path(clone: Path, rel: str) -> str:
    """Where the clone already keeps `rel` (any letter case, GitHub's alternate dirs); else `rel`.

    Writing to the existing file avoids a second copy that differs only in case, which a
    case-insensitive filesystem merges and git then tracks twice.
    """
    candidates = [rel]
    if rel in ALT_LOCATION_FILES:
        name = Path(rel).name
        candidates += [str(Path(directory) / name) for directory in GITHUB_ALT_DIRS]
    for candidate in candidates:
        found = _existing_spelling(clone, candidate)
        if found is not None:
            return found
    return rel


def marked_region(text: str, markers: tuple[str, str]) -> str:
    """The marker-delimited part of a rendered template (markers included)."""
    match = _marker_re(markers).search(text)
    if match is None:
        raise ValueError(f"template has no {markers[0]} section")
    return match.group(0)


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def plan_repo(clone: Path, repo: repos.Repo, manifest: repos.Manifest, ref: str) -> Plan:
    plan = Plan(writes={}, diffs=[], notes=[])

    def propose(rel: str, old: str | None, new: str) -> None:
        if old != new:
            plan.writes[rel] = new
            plan.diffs.append(_diff(rel, old, new))

    for name, rel in MANAGED_FILES.items():
        rel = resolve_path(clone, rel)
        propose(rel, _read(clone, rel), render(_template(name), repo, manifest, ref))

    if repo.lint_rules:
        template = _template(LINT_TEMPLATE).replace("{{lint_setup}}", lint_setup(repo))
        propose(LINT_WORKFLOW, _read(clone, LINT_WORKFLOW), render(template, repo, manifest, ref))

    for name, rel in CREATE_ONLY_FILES.items():
        rel = resolve_path(clone, rel)
        existing = _read(clone, rel)
        if existing is None:
            propose(rel, None, render(_template(name), repo, manifest, ref))
        elif existing != render(_template(name), repo, manifest, ref):
            plan.notes.append(f"{rel} exists and was left untouched")

    for name, rel, markers, fallback in MARKED_FILES:
        rendered = render(_template(name), repo, manifest, ref)
        block = marked_region(rendered, markers)
        rel = resolve_path(clone, rel)
        existing = _read(clone, rel)
        if existing is None:
            propose(rel, None, rendered)
            continue
        replaced = replace_marked(existing, block, markers)
        if replaced is not None:
            propose(rel, existing, replaced)
        elif fallback == "append":
            separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
            propose(rel, existing, existing + separator + block)
        else:
            plan.notes.append(
                f"{rel} needs manual merge: it exists without leapwell markers ({markers[0]} ... {markers[1]})"
            )
    return plan


def git(clone: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=clone, capture_output=True, text=True)
    if done.returncode != 0:
        raise SyncError(f"git {args[0]} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def _branch_exists(clone: Path, branch: str) -> bool:
    done = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=clone, capture_output=True, text=True
    )
    return done.returncode == 0


def _write(clone: Path, writes: dict[str, str]) -> None:
    for rel, content in writes.items():
        path = clone / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(content)


def sync_repo(clone: Path, repo: repos.Repo, manifest: repos.Manifest, ref: str, apply: bool) -> Plan:
    """Sync one clone. Raises SyncError when it is missing, dirty or git fails."""
    if not (clone / ".git").exists():
        raise SyncError("not cloned — run /lw-setup")
    if git(clone, "status", "--porcelain").strip():
        raise SyncError("working tree is dirty; commit or stash first")
    plan = plan_repo(clone, repo, manifest, ref)
    if not apply or not plan.changed:
        return plan
    if git(clone, "rev-parse", "--abbrev-ref", "HEAD").strip() != SYNC_BRANCH:
        if _branch_exists(clone, SYNC_BRANCH):
            git(clone, "checkout", SYNC_BRANCH)
        else:
            git(clone, "checkout", "-b", SYNC_BRANCH)
        plan = plan_repo(clone, repo, manifest, ref)
    if plan.changed:
        _write(clone, plan.writes)
        git(clone, "add", "--", *plan.writes)
        git(clone, "commit", "-m", f"chore(sync): apply leapwell thin layer ({ref})")
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repo", help="repo key from repos.json")
    target.add_argument("--all", action="store_true", help="every repo in repos.json")
    parser.add_argument(
        "--ref", default=DEFAULT_REF, help="leapwell sha or tag the workflows check out (default: main)"
    )
    parser.add_argument("--apply", action="store_true", help=f"commit on local branch {SYNC_BRANCH} (default: dry-run)")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="directory holding the clones")
    args = parser.parse_args(argv)
    try:
        manifest = repos.load()
        selected = manifest.repos if args.all else (manifest.by_key(args.repo),)
    except (ValueError, OSError, KeyError) as exc:
        print(f"sync: {exc}", file=sys.stderr)
        return 1

    failed = False
    for repo in selected:
        print(f"== {repo.key} ({repo.name})")
        try:
            plan = sync_repo(Path(args.workspace) / repo.name, repo, manifest, args.ref, args.apply)
        except SyncError as exc:
            print(f"  refused: {exc}")
            failed = True
            continue
        for note in plan.notes:
            print(f"  note: {note}")
        if not plan.changed:
            print("  up to date")
            continue
        if args.apply:
            print(f"  committed {len(plan.writes)} file(s) on {SYNC_BRANCH} (not pushed)")
        else:
            print("".join(plan.diffs), end="")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
