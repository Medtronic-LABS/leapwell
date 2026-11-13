"""Validate a GitHub issue against the LEAPWELL intake contract.

CLI: python3 scripts/sdlc/check_issue.py --event "$GITHUB_EVENT_PATH" [--scan-only]
--scan-only skips the intake-section checks and only scans for sensitive data (for drafts that
are not intake issues, e.g. routed sub-issues).
Prints JSON {"ok", "comment", "marker", "needs_info_label"} and exits 0; the workflow decides labels.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.sdlc.patterns import (  # noqa: E402
    PRIVACY_HEADING,
    REQUIRED_SECTIONS,
    TITLE_PREFIXES,
    TYPE_LABELS,
    find_sensitive,
)

COMMENT_MARKER = "<!-- lw-issue-check -->"
NEEDS_INFO_LABEL = "status:needs-info"
_HEADING_RE = re.compile(r"^###[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_TICKED_RE = re.compile(r"-\s*\[[xX]\]")
_EMPTY_VALUES = {"", "_no response_"}
UNKNOWN_COMPONENT_HEADING = "Repo or component (if known)"
_UNKNOWN_COMPONENT_VALUES = _EMPTY_VALUES | {"don't know"}
ROUTED_LABEL = "status:routed"
AREA_PREFIX = "area:"


@dataclass
class IssueResult:
    issue_type: str | None
    missing: list[str] = field(default_factory=list)
    privacy_unchecked: bool = False
    sensitive: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.privacy_unchecked or self.sensitive)


def parse_sections(body: str) -> dict[str, str]:
    """Split a Markdown issue body into {heading: content} for `### Heading` blocks."""
    matches = list(_HEADING_RE.finditer(body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1)] = body[match.end() : end].strip()
    return sections


def detect_type(title: str, labels: list[str]) -> str | None:
    for label, issue_type in TYPE_LABELS.items():
        if label in labels:
            return issue_type
    lowered = title.strip().lower()
    for prefix, issue_type in TITLE_PREFIXES.items():
        if lowered.startswith(prefix):
            return issue_type
    return None


def _is_empty(value: str) -> bool:
    return value.strip().lower() in _EMPTY_VALUES


def evaluate(title: str, body: str, labels: list[str]) -> IssueResult:
    """Check required sections, the privacy tick-box and sensitive data."""
    issue_type = detect_type(title, labels)
    result = IssueResult(issue_type=issue_type, sensitive=find_sensitive(f"{title}\n{body}"))
    if issue_type is None:
        return result
    sections = parse_sections(body)
    required = REQUIRED_SECTIONS[issue_type]
    result.missing = [h for h in required if _is_empty(sections.get(h, ""))]
    if PRIVACY_HEADING in required:
        result.privacy_unchecked = not _TICKED_RE.search(sections.get(PRIVACY_HEADING, ""))
    return result


def scan_only(title: str, body: str) -> IssueResult:
    """Sensitive-data scan only; no intake sections required (ok iff nothing sensitive was found)."""
    return IssueResult(issue_type=None, sensitive=find_sensitive(f"{title}\n{body}"))


def needs_triage(title: str, body: str, labels: list[str]) -> bool:
    """True for a bug with an unknown component that nobody has routed or area-labelled yet."""
    if ROUTED_LABEL in labels or any(label.startswith(AREA_PREFIX) for label in labels):
        return False
    if detect_type(title, labels) != "bug":
        return False
    component = parse_sections(body).get(UNKNOWN_COMPONENT_HEADING, "")
    normalised = component.replace("\u2019", "'").replace("\u2018", "'").strip().lower()
    return normalised in _UNKNOWN_COMPONENT_VALUES


def render_comment(result: IssueResult) -> str:
    """Bot comment text; lists headings and categories only, never matched values."""
    lines = [COMMENT_MARKER]
    if result.ok:
        lines.append("Intake check passed. Thanks for the complete report.")
        return "\n".join(lines)
    lines.append("This issue needs a few changes before it can be triaged. Please edit the issue description.")
    if result.missing:
        lines.append("\nMissing or empty sections:")
        lines.extend(f"- {heading}" for heading in result.missing)
    if result.privacy_unchecked:
        lines.append(f"\nThe **{PRIVACY_HEADING}** box is not ticked. Confirm no patient data or secrets are included.")
    if result.sensitive:
        lines.append(
            "\nPossible sensitive data detected (types only): "
            + ", ".join(result.sensitive)
            + ". This repository is public: remove it from the issue, then rotate any exposed credential."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="path to the GitHub event JSON")
    parser.add_argument("--scan-only", action="store_true", help="only scan for sensitive data")
    args = parser.parse_args(argv)
    issue = json.loads(Path(args.event).read_text(encoding="utf-8"))["issue"]
    labels = [label["name"] for label in issue.get("labels") or []]
    title, body = issue.get("title") or "", issue.get("body") or ""
    result = scan_only(title, body) if args.scan_only else evaluate(title, body, labels)
    print(
        json.dumps(
            {
                "ok": result.ok,
                "comment": render_comment(result),
                "marker": COMMENT_MARKER,
                "needs_info_label": NEEDS_INFO_LABEL,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
