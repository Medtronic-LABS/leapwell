"""Scan text files under the given directories for patient data and secrets.

CLI: python3 scripts/sdlc/scan_text.py <dir>...
Prints `path:line: category` (never the matched text) and exits 1 on any finding.
Directories that do not exist are skipped.
"""
import sys
from pathlib import Path
from typing import Iterable, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc.patterns import find_sensitive  # noqa: E402

TEXT_SUFFIXES = frozenset({".md", ".html", ".svg", ".txt", ".json", ".csv"})


def scan_dirs(directories: Iterable[Path]) -> list[tuple[Path, int, list[str]]]:
    """Return (file, line number, categories) for every line with sensitive data."""
    findings: list[tuple[Path, int, list[str]]] = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES):
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                categories = find_sensitive(line)
                if categories:
                    findings.append((path, number, categories))
    return findings


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: scan_text.py <dir>...", file=sys.stderr)
        return 2
    findings = scan_dirs(Path(a) for a in args)
    for path, number, categories in findings:
        print(f"{path}:{number}: {', '.join(categories)}")
    if findings:
        print(f"{len(findings)} line(s) with possible sensitive data; remove it (fake data only).", file=sys.stderr)
        return 1
    print("No sensitive data found in scanned text files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
