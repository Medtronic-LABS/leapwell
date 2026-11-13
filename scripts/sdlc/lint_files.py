"""Lint the changed files of the current repo with its `lint_rules` from repos.json.

CLI (run from inside the repo):
  python3 scripts/sdlc/lint_files.py --staged      pre-commit: staged files; skipped when the repo
                                                   has its own pre-commit setup (pre-commit framework
                                                   or husky), which the hook chain runs instead
  python3 scripts/sdlc/lint_files.py --base REF    CI: files changed in REF...HEAD
  python3 scripts/sdlc/lint_files.py --all         every tracked file (leapwell's own CI)

leapwell itself uses `hub_lint_rules`; a code repo is found by its `origin` remote name. Each rule's
command gets the matching paths appended. A failing command or a missing tool exits 1.
"""

import argparse
import fnmatch
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc import repos  # noqa: E402
from scripts.sdlc.repos import LintRule  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CHUNK = 200
OWN_PRECOMMIT_FILES = (".pre-commit-config.yaml", ".husky/pre-commit")

Runner = Callable[[list[str], Path], int]
Which = Callable[[str], str | None]


def select(paths: Sequence[str], globs: Sequence[str]) -> list[str]:
    """Paths matching any glob; `*` also matches `/`, so `*.py` covers nested files."""
    return sorted(p for p in paths if any(fnmatch.fnmatchcase(p, g) for g in globs))


def remote_repo_name(url: str) -> str:
    """`beta` from https://github.com/O/beta(.git) or git@github.com:O/beta.git."""
    last = url.strip().rstrip("/").replace(":", "/").rsplit("/", 1)[-1]
    return last[:-4] if last.endswith(".git") else last


def rules_for(manifest: repos.Manifest, *, is_hub: bool, name: str) -> tuple[LintRule, ...]:
    if is_hub:
        return manifest.hub_lint_rules
    try:
        return manifest.by_name(name).lint_rules
    except KeyError:
        return ()


def _run(cmd: list[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=cwd, check=False).returncode


def run_rules(
    rules: Sequence[LintRule],
    paths: Sequence[str],
    root: Path,
    *,
    which: Which = shutil.which,
    runner: Runner = _run,
) -> list[str]:
    """Run each rule on its matching paths; return one problem line per failed or missing tool."""
    problems = []
    for rule in rules:
        files = select(paths, rule.files)
        if not files:
            continue
        command = shlex.split(rule.run)
        if which(command[0]) is None:
            problems.append(f"`{command[0]}` is not installed; it is needed to lint {', '.join(rule.files)} files")
            continue
        print(f"lw-lint: {rule.run} ({len(files)} file{'s' if len(files) != 1 else ''})", flush=True)
        failed = False
        for start in range(0, len(files), CHUNK):
            failed |= runner(command + files[start : start + CHUNK], root) != 0
        if failed:
            problems.append(f"`{rule.run}` reported problems")
    return problems


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def changed_paths(root: Path, mode: str, base: str | None) -> list[str]:
    if mode == "staged":
        out = _git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    elif mode == "base":
        out = _git(root, "diff", "--name-only", "--diff-filter=ACMR", "-z", f"{base}...HEAD")
    else:
        out = _git(root, "ls-files", "-z")
    return [p for p in out.split("\0") if p and (root / p).is_file()]


def _origin_name(root: Path) -> str:
    done = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True, check=False)
    return remote_repo_name(done.stdout) if done.returncode == 0 and done.stdout.strip() else root.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint changed files with the repo's lint_rules from repos.json")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true", help="staged files (pre-commit)")
    mode.add_argument("--base", metavar="REF", help="files changed in REF...HEAD (CI)")
    mode.add_argument("--all", action="store_true", help="every tracked file")
    args = parser.parse_args(argv)

    root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip()).resolve()
    is_hub = root == ROOT.resolve()
    if args.staged and not is_hub and any((root / f).is_file() for f in OWN_PRECOMMIT_FILES):
        print("lw-lint: this repo has its own pre-commit setup; the hook chain runs it instead")
        return 0
    try:
        rules = rules_for(repos.load(), is_hub=is_hub, name=_origin_name(root))
    except (ValueError, OSError) as exc:
        print(f"lw-lint: cannot read repos.json: {exc}", file=sys.stderr)
        return 1
    if not rules:
        return 0
    mode_name = "staged" if args.staged else "base" if args.base else "all"
    problems = run_rules(rules, changed_paths(root, mode_name, args.base), root)
    for problem in problems:
        print(f"lw-lint: {problem}", file=sys.stderr)
    if problems:
        print("lw-lint: fix the problems above (or install the missing tool) and commit again.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
