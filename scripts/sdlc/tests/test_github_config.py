"""Static checks of the leapwell GitHub layer: forms, labels, workflows, ownership."""
import re
import unittest
from pathlib import Path

from scripts.sdlc import repos
from scripts.sdlc.patterns import REQUIRED_SECTIONS

ROOT = Path(__file__).resolve().parents[3]
GITHUB = ROOT / ".github"
EXPECTED_JOBS = {
    "ci.yml": {"sdlc-scripts", "secret-scan", "mockup-scan"},
    "pr-check.yml": {"pr-check"},
    "close-parents.yml": {"close-parents"},
    "issue-check.yml": {"issue-check"},
}
DISCUSSION_FORMS = ("ideas", "field-feedback", "partner-requests")
LABEL_REF_RE = re.compile(r"\b(?:status|type|prio|env):[A-Za-z][\w-]*")


def read(rel):
    return (GITHUB / rel).read_text(encoding="utf-8")


def label_names():
    names = re.findall(r"^- name:\s*(.+?)\s*$", read("labels.yml"), re.MULTILINE)
    return [n.strip("\"'") for n in names]


def field_labels(text):
    """Top-level field labels of an issue/discussion form (6-space indent under attributes)."""
    return re.findall(r"^      label:\s*(.+?)\s*$", text, re.MULTILINE)


class IssueFormsTest(unittest.TestCase):
    def test_forms_carry_required_headings(self):
        for issue_type, required in REQUIRED_SECTIONS.items():
            labels = field_labels(read(f"ISSUE_TEMPLATE/{issue_type}.yml"))
            for heading in required:
                self.assertIn(heading, labels, f"{issue_type} form lacks '{heading}'")

    def test_forms_apply_type_label_and_title_prefix(self):
        for issue_type in REQUIRED_SECTIONS:
            text = read(f"ISSUE_TEMPLATE/{issue_type}.yml")
            self.assertRegex(text, rf'(?m)^labels: \["type:{issue_type}"\]$')
            self.assertIn(f'title: "[{issue_type.capitalize()}] "', text)

    def test_issue_forms_end_with_required_privacy_checkbox(self):
        for issue_type in ("bug", "feature", "task"):
            self.assert_privacy_last(read(f"ISSUE_TEMPLATE/{issue_type}.yml"))

    def test_bug_repo_dropdown_matches_manifest_areas(self):
        text = read("ISSUE_TEMPLATE/bug.yml")
        block = text.split("label: Repo or component (if known)", 1)[1].split("validations:", 1)[0]
        options = re.findall(r"^        - (.+)$", block, re.MULTILINE)
        areas = list(dict.fromkeys(r.area for r in repos.load().repos))
        self.assertEqual(options, areas + ["Don't know"])
        self.assertRegex(text.split("validations:", 1)[1].split("- type:", 1)[0], r"required: false")

    def test_config_disables_blank_issues_and_points_to_discussions(self):
        text = read("ISSUE_TEMPLATE/config.yml")
        self.assertIn("blank_issues_enabled: false", text)
        self.assertIn("https://github.com/Medtronic-LABS/leapwell/discussions", text)
        self.assertIn("security/advisories/new", text)

    def assert_privacy_last(self, text):
        self.assertTrue(text.rstrip().endswith("required: true"))
        tail = text.split("  - type: checkboxes")[-1]
        self.assertIn("label: Privacy check", tail)
        self.assertIn("(this repo is public)", tail)


class DiscussionFormsTest(unittest.TestCase):
    def test_filenames_are_category_slugs(self):
        found = sorted(p.stem for p in (GITHUB / "DISCUSSION_TEMPLATE").glob("*.yml"))
        self.assertEqual(found, sorted(DISCUSSION_FORMS))

    def test_each_form_ends_with_required_privacy_checkbox(self):
        for slug in DISCUSSION_FORMS:
            text = read(f"DISCUSSION_TEMPLATE/{slug}.yml")
            self.assertTrue(text.rstrip().endswith("required: true"), slug)
            self.assertIn("label: Privacy check", text.split("  - type: checkboxes")[-1], slug)

    def test_form_fields(self):
        expected = {
            "ideas": ["Problem", "Who is affected", "Your idea", "Evidence", "Privacy check"],
            "field-feedback": ["Where and when", "What happened", "Impact on the work", "Privacy check"],
            "partner-requests": ["Partner type", "Request", "Deadline", "Privacy check"],
        }
        for slug, labels in expected.items():
            self.assertEqual(field_labels(read(f"DISCUSSION_TEMPLATE/{slug}.yml")), labels, slug)


class LabelsTest(unittest.TestCase):
    def test_labels_unique_and_complete(self):
        names = label_names()
        self.assertEqual(len(names), len(set(names)))
        required = {"documentation", "duplicate", "good first issue",
                    "help wanted", "invalid", "question", "wontfix", "refactor", "tech-debt",
                    "prio:P0", "prio:P1", "prio:P2", "prio:P3",
                    "env:prod", "env:training", "env:dev", "status:blocked", "status:needs-design",
                    "type:bug", "type:feature", "type:task", "type:release",
                    "status:needs-info", "status:routed", "status:triage"}
        required |= {f"area:{a}" for a in (
            "auth sync db visit cdss scribe teleconsult household push release ci i18n").split()}
        self.assertLessEqual(required, set(names))
        for legacy in ("bug", "enhancement", "chore", "release"):
            self.assertNotIn(legacy, names, "type:* is the only type-label contract")
        self.assertRegex(read("labels.yml"), r"- name: type:bug\n  color: \"?d73a4a")

    def test_area_label_for_every_repo_key(self):
        names = set(label_names())
        for repo in repos.load().repos:
            self.assertIn(f"area:{repo.key}", names)

    def test_labels_referenced_by_workflows_and_forms_exist(self):
        names = set(label_names())
        sources = list((GITHUB / "workflows").glob("*.yml")) + list((GITHUB / "ISSUE_TEMPLATE").glob("*.yml"))
        claude = ROOT / ".claude"
        if claude.is_dir():
            sources += [p for p in claude.rglob("*.md") if p.is_file()]
        for path in sources:
            for ref in LABEL_REF_RE.findall(path.read_text(encoding="utf-8")):
                self.assertIn(ref, names, f"{path.relative_to(ROOT)} references unknown label {ref}")


class RepoFilesTest(unittest.TestCase):
    def test_pr_template(self):
        text = read("pull_request_template.md")
        for needle in ("Closes #", "## Summary", "Test evidence", "Risk & rollback"):
            self.assertIn(needle, text)

    def test_codeowners(self):
        text = read("CODEOWNERS")
        self.assertIn("* @Medtronic-LABS/leapfrogging", text)
        for path in ("/.github/", "/scripts/", "/.claude/", "/templates/", "/repos.json"):
            self.assertRegex(text, rf"(?m)^{re.escape(path)}\s+@amreshyadavgit @adityab24840")


class WorkflowsTest(unittest.TestCase):
    def test_job_ids(self):
        for name, jobs in EXPECTED_JOBS.items():
            after_jobs = read(f"workflows/{name}").split("\njobs:", 1)[1]
            found = set(re.findall(r"^  ([\w-]+):\s*$", after_jobs, re.MULTILINE))
            self.assertEqual(found, jobs, name)

    def test_ci_has_no_flutter_and_pins_gitleaks(self):
        text = read("workflows/ci.yml")
        self.assertNotIn("flutter", text)
        self.assertIn("GITLEAKS_VERSION: 8.24.3", text)
        self.assertIn("--redact", text)
        self.assertIn("fetch-depth: 0", text)
        self.assertIn("scan_text.py mockups wiki", text)

    def test_close_parents_schedule_and_permissions(self):
        text = read("workflows/close-parents.yml")
        self.assertIn("cron: '17 * * * *'", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("issues: write", text)
        self.assertIn("contents: read", text)
        self.assertIn("GH_TOKEN: ${{ secrets.LEAPWELL_BOT_TOKEN || secrets.GITHUB_TOKEN }}", text)
        self.assertIn("group: close-parents", text)
        self.assertIn("close_parents.py --apply", text)

    def test_issue_check_flags_unknown_component_for_triage(self):
        text = read("workflows/issue-check.yml")
        self.assertIn("status:triage", text)
        self.assertIn("needs_triage", text)
        self.assertNotIn("label create", text, "labels come from labels.yml, not the workflow")


if __name__ == "__main__":
    unittest.main()
