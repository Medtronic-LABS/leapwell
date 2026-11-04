"""Typed access to the repos manifest (`repos.json`), the single home for repo facts.

`load()` honours the `LW_REPOS_JSON` environment variable (a path) so tests and
tooling can point at another manifest.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "repos.json"
ENV_OVERRIDE = "LW_REPOS_JSON"

_TOP_KEYS = ("org", "tracker", "project", "repos")
_REPO_STR_KEYS = ("key", "name", "area", "stack", "integration_branch")
_VERIFY_KEYS = ("test", "lint", "build")


@dataclass(frozen=True)
class Repo:
    key: str
    name: str
    area: str
    stack: str
    integration_branch: str
    protected_branches: tuple[str, ...]
    verify: dict[str, str]


@dataclass(frozen=True)
class Manifest:
    org: str
    tracker: str
    project: int
    repos: tuple[Repo, ...]

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
    return Repo(
        key=entry["key"], name=entry["name"], area=entry["area"], stack=entry["stack"],
        integration_branch=entry["integration_branch"],
        protected_branches=tuple(protected),
        verify={k: verify[k] for k in _VERIFY_KEYS},
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
    return Manifest(org=data["org"], tracker=data["tracker"], project=data["project"], repos=repos)


def load(path: Optional[os.PathLike] = None) -> Manifest:
    """Load and validate the manifest; raises ValueError naming the bad entry."""
    source = Path(path) if path else Path(os.environ.get(ENV_OVERRIDE) or DEFAULT_PATH)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid JSON ({exc})") from exc
    return parse(data)
