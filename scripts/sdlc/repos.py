"""Typed access to the repos manifest (`repos.json`), the single home for repo facts.

`load()` honours the `LW_REPOS_JSON` environment variable (a path) so tests and
tooling can point at another manifest.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "repos.json"
ENV_OVERRIDE = "LW_REPOS_JSON"

_TOP_KEYS = ("org", "tracker", "project", "repos")
_REPO_STR_KEYS = ("key", "name", "area", "stack", "integration_branch")
_VERIFY_KEYS = ("test", "lint", "build")


@dataclass(frozen=True)
class LintRule:
    """Lint command run on the changed files matching `files` (fnmatch globs on repo-relative paths)."""

    files: tuple[str, ...]
    run: str


@dataclass(frozen=True)
class Repo:
    key: str
    name: str
    area: str
    stack: str
    integration_branch: str
    protected_branches: tuple[str, ...]
    verify: dict[str, str]
    notes: str = ""
    lint_rules: tuple[LintRule, ...] = ()


@dataclass(frozen=True)
class Manifest:
    org: str
    tracker: str
    project: int
    repos: tuple[Repo, ...]
    hub_lint_rules: tuple[LintRule, ...] = ()

    @property
    def tracker_slug(self) -> str:
        return f"{self.org}/{self.tracker}"

    def by_key(self, key: str) -> Repo:
        return self._find("key", key)

    def by_name(self, name: str) -> Repo:
        return self._find("name", name)

    def _find(self, attr: str, value: str) -> Repo:
        for repo in self.repos:
            if getattr(repo, attr) == value:
                return repo
        raise KeyError(f"no repo with {attr} {value!r}")

    def protected_branches(self) -> set[str]:
        return {branch for repo in self.repos for branch in repo.protected_branches}


def _parse_lint_rules(value: Any, label: str) -> tuple[LintRule, ...]:
    """Optional list of {"files": [glob, ...], "run": "command"}; absent means no rules."""
    if value is None:
        return ()
    error = f"{label}: 'lint_rules' must be a list of {{'files': [glob, ...], 'run': command}}"
    if not isinstance(value, list):
        raise ValueError(error)
    rules = []
    for rule in value:
        files = rule.get("files") if isinstance(rule, dict) else None
        run = rule.get("run") if isinstance(rule, dict) else None
        if not isinstance(files, list) or not files or not all(isinstance(f, str) and f for f in files):
            raise ValueError(error)
        if not isinstance(run, str) or not run.strip():
            raise ValueError(error)
        rules.append(LintRule(files=tuple(files), run=run))
    return tuple(rules)


def _parse_repo(entry: Any, index: int) -> Repo:
    label = f"repos[{index}]"
    if not isinstance(entry, dict):
        raise ValueError(f"{label}: must be an object")
    if isinstance(entry.get("key"), str):
        label = f"repos[{index}] ({entry['key']})"
    for name in _REPO_STR_KEYS:
        if not isinstance(entry.get(name), str) or not entry[name]:
            raise ValueError(f"{label}: missing or empty '{name}'")
    protected = entry.get("protected_branches")
    if not isinstance(protected, list) or not protected or not all(isinstance(b, str) for b in protected):
        raise ValueError(f"{label}: 'protected_branches' must be a non-empty list of strings")
    verify = entry.get("verify")
    if not isinstance(verify, dict) or any(not isinstance(verify.get(k), str) for k in _VERIFY_KEYS):
        raise ValueError(f"{label}: 'verify' must define string values for {', '.join(_VERIFY_KEYS)}")
    notes = entry.get("notes", "")
    if not isinstance(notes, str):
        raise ValueError(f"{label}: 'notes' must be a string")
    return Repo(
        notes=notes,
        key=entry["key"],
        name=entry["name"],
        area=entry["area"],
        stack=entry["stack"],
        integration_branch=entry["integration_branch"],
        protected_branches=tuple(protected),
        verify={k: verify[k] for k in _VERIFY_KEYS},
        lint_rules=_parse_lint_rules(entry.get("lint_rules"), label),
    )


def parse(data: Any) -> Manifest:
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    for name in _TOP_KEYS:
        if name not in data:
            raise ValueError(f"manifest: missing '{name}'")
    if not isinstance(data["repos"], list):
        raise ValueError("manifest: 'repos' must be a list")
    repos = tuple(_parse_repo(entry, i) for i, entry in enumerate(data["repos"]))
    return Manifest(
        org=data["org"],
        tracker=data["tracker"],
        project=data["project"],
        repos=repos,
        hub_lint_rules=_parse_lint_rules(data.get("hub_lint_rules"), "manifest (hub_lint_rules)"),
    )


def load(path: os.PathLike | None = None) -> Manifest:
    """Load and validate the manifest; raises ValueError naming the bad entry."""
    source = Path(path) if path else Path(os.environ.get(ENV_OVERRIDE) or DEFAULT_PATH)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid JSON ({exc})") from exc
    return parse(data)


def main(argv: list[str] | None = None) -> int:
    """CLI for shell scripts: `--list` prints `key name integration_branch` per repo;
    `--get org|tracker|project` prints one top-level fact."""
    parser = argparse.ArgumentParser(description="Read facts from repos.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="print 'key name integration_branch' per repo")
    group.add_argument("--get", choices=("org", "tracker", "project"), help="print one top-level fact")
    args = parser.parse_args(argv)
    try:
        manifest = load()
    except (ValueError, OSError) as exc:
        print(f"repos: {exc}", file=sys.stderr)
        return 1
    if args.list:
        for repo in manifest.repos:
            print(repo.key, repo.name, repo.integration_branch)
    else:
        print(getattr(manifest, args.get))
    return 0


if __name__ == "__main__":
    sys.exit(main())
