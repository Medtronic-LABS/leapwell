"""Tool check for the LeapWell workspace: which required tools are missing, per repo area.

Informational (exit 0) unless --strict. `which` and `run` are injectable for tests.
"""

import argparse
import shutil
import subprocess
import sys
from collections.abc import Callable

from scripts.sdlc import repos

MIN_PYTHON = (3, 11)
BASE_TOOLS = ("git", "gh", "python3")
AREA_TOOLS = {
    "Mobile app": ("flutter", "java"),
    "Frappe apps": ("docker",),
    "AI Scribe": ("docker", "python3"),
    "Micro-coaching": ("docker", "node", "npm", "java"),
}

Which = Callable[[str], str | None]
Run = Callable[[list[str]], int]


def _run(command: list[str]) -> int:
    try:
        return subprocess.run(command, capture_output=True, timeout=20).returncode
    except (OSError, subprocess.SubprocessError):
        return 1


def required_tools(areas: list[str]) -> dict[str, list[str]]:
    """tool -> sorted reasons ('workspace' or an area)."""
    needs: dict[str, set[str]] = {tool: {"workspace"} for tool in BASE_TOOLS}
    for area in areas:
        for tool in AREA_TOOLS.get(area, ()):
            needs.setdefault(tool, set()).add(area)
    return {tool: sorted(reasons) for tool, reasons in needs.items()}


def check(
    areas: list[str], which: Which = shutil.which, run: Run = _run, python_version: tuple = tuple(sys.version_info[:2])
) -> list[tuple[str, str, str]]:
    """Rows of (tool, status, detail); status is 'ok', 'MISSING' or 'FAIL'."""
    rows = []
    for tool, reasons in required_tools(areas).items():
        detail = "needed by " + ", ".join(reasons)
        if which(tool) is None:
            rows.append((tool, "MISSING", detail))
        elif tool == "python3" and tuple(python_version) < MIN_PYTHON:
            rows.append((tool, "FAIL", "python >= {}.{} required".format(*MIN_PYTHON)))
        elif tool == "gh" and run(["gh", "auth", "status"]) != 0:
            rows.append((tool, "FAIL", "not authenticated: run `gh auth login`"))
        else:
            rows.append((tool, "ok", detail))
    return rows


def render(rows: list[tuple[str, str, str]]) -> str:
    width = max(len(row[0]) for row in rows)
    return "\n".join(f"{tool.ljust(width)}  {status.ljust(7)}  {detail}" for tool, status, detail in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check tools needed by the LeapWell repos")
    parser.add_argument("--only", default="", help="comma-separated repo keys (default: all)")
    parser.add_argument("--strict", action="store_true", help="exit 1 if anything is missing")
    args = parser.parse_args(argv)
    manifest = repos.load()
    keys = [k for k in args.only.split(",") if k]
    selected = [r for r in manifest.repos if not keys or r.key in keys]
    rows = check(sorted({r.area for r in selected}))
    print(render(rows))
    bad = [row for row in rows if row[1] != "ok"]
    if bad:
        print(f"\n{len(bad)} tool(s) need attention.")
    return 1 if bad and args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
