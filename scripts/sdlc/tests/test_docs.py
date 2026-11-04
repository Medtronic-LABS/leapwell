"""Checks for the process docs, wiki seed, mockups folder, CLAUDE.md and README."""
import json
import re
import unittest
from pathlib import Path

from scripts.sdlc.patterns import find_sensitive

ROOT = Path(__file__).resolve().parents[3]
PROCESS = ROOT / "docs" / "process"
WIKI = ROOT / "wiki"
MOCKUPS = ROOT / "mockups"
DOCS = ("SDLC.md", "TICKETS.md", "REQUIREMENTS.md", "ADMIN_SETUP.md", "REPOS.md")
FEATURE_PAGES = (
    "Feature-AI-Scribe", "Feature-Visit-Briefing", "Feature-Micro-Coaching", "Feature-Visit-Flow-and-CDSS",
    "Feature-Teleconsult-Shukhee", "Feature-Household-and-Enrolment", "Feature-Sync-and-Offline",
)
WIKI_PAGES = ("Home", "Project-Overview", "Repos-and-Areas", "Glossary") + FEATURE_PAGES
STATUS_FLOW = ("Triage", "Backlog", "Ready", "In progress", "In review", "QA", "Done")
JIRA_KEY_RE = re.compile(r"\bLEAP-\d")
URL_RE = re.compile(r"https?://[^\s)>`\"']+")
ALLOWED_URL_PREFIXES = ("https://github.com/Medtronic-LABS/", "http://localhost")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
STANDARDS_LABELS = (
    "OOP & SOLID", "DRY / reuse", "Modularity & separation of concerns", "Abstraction",
    "Configuration management", "Localization", "Error handling", "Maintainability", "Scalability",
)


def read(path):
    return path.read_text(encoding="utf-8")


def names_in(directory, pattern):
    return sorted(p.parent.name if p.name == "SKILL.md" else p.stem for p in directory.glob(pattern))


def public_text_files():
    files = [PROCESS / n for n in DOCS] + [ROOT / "CLAUDE.md", ROOT / "README.md"]
    files += sorted(WIKI.glob("*.md")) + sorted(MOCKUPS.rglob("*.md"))
    return files


def manifest_repos():
    return json.loads(read(ROOT / "repos.json"))["repos"]


def table_rows(text, heading_cell):
    """Rows of the first markdown table whose header starts with `heading_cell`, as cell lists."""
    rows, in_table = [], False
    for line in text.splitlines():
        if line.startswith(f"| {heading_cell} |"):
            in_table = True
        elif in_table and line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif in_table:
            break
    return rows[1:]  # drop the header separator row


class ProcessDocsTest(unittest.TestCase):
    def test_docs_exist(self):
        for name in DOCS:
            self.assertTrue((PROCESS / name).is_file(), f"docs/process/{name} missing")

    def test_sdlc_mentions_every_skill_and_agent(self):
        sdlc = read(PROCESS / "SDLC.md")
        names = names_in(ROOT / ".claude/skills", "*/SKILL.md") + names_in(ROOT / ".claude/agents", "*.md")
        self.assertTrue(names)
        for name in names:
            self.assertIn(name, sdlc, f"SDLC.md does not mention {name}")

    def test_sdlc_sections(self):
        sdlc = read(PROCESS / "SDLC.md")
        for phrase in ("Definition of Ready", "Definition of Done", "Branching", "CI gates", "Hotfix",
                       "RELEASE_PLAN.md", "gh auth refresh -s project", ".superpowers/sdd/", "Closes #n",
                       "Refs Medtronic-LABS/leapwell#N", "lw-close-on-merge", "close-parents", "status:routed",
                       "judged by nature, not line count", "Jira"):
            self.assertIn(phrase, sdlc)
        for size in ("| S |", "| M |", "| L |"):
            self.assertIn(size, sdlc)
        self.assertNotIn("400", sdlc)
        self.assertIn(" → ".join(STATUS_FLOW), sdlc)

    def test_sdlc_points_at_budgets_without_copying_them(self):
        sdlc = read(PROCESS / "SDLC.md")
        for var in ("ANALYZE_ERROR_BUDGET", "TEST_FAILURE_BUDGET"):
            self.assertIn(var, sdlc)
            self.assertNotRegex(sdlc, rf"{var}`?\s*[=:]\s*\d")

    def test_doc_lengths(self):
        self.assertLessEqual(len(read(PROCESS / "SDLC.md").splitlines()), 300)
        self.assertLessEqual(len(read(PROCESS / "TICKETS.md").splitlines()), 80)

    def test_tickets_guide_covers_intake(self):
        tickets = read(PROCESS / "TICKETS.md")
        for phrase in ("/lw-ticket", "file a bug", "public", "Discussion", "Triage", "screenshot",
                       "issues/new/choose", "status:routed"):
            self.assertIn(phrase, tickets)

    def test_requirements_covers_flow(self):
        text = read(PROCESS / "REQUIREMENTS.md")
        for phrase in ("/lw-promote", "/lw-route", "close-parents", "sub-issue", "/lw-wiki", "mockups/<feature-slug>/",
                       "mockup-scan", "Fake data only", "Wiki rules", "Mockup rules"):
            self.assertIn(phrase, text)

    def test_admin_setup_covers_owner_steps(self):
        admin = read(PROCESS / "ADMIN_SETUP.md").lower()
        for phrase in ("dist/skills/lw-ticket.zip", "package_skill.sh", "sync_labels.sh", "setup_discussions.sh",
                       "setup_project.sh", "publish_wiki.sh", "protect_branches.sh", "sync_repos.py", "--apply",
                       "leapwell_bot_token", "issues: read", "issues: write", "60 days", "workflow_dispatch",
                       "private vulnerability reporting", "settings.local.json", "open decisions",
                       "env.staging.json", "frappe v16", "triage", "first page",
                       "item added to project", "item closed", "pull request merged", "item reopened",
                       "auto-add to project"):
            self.assertIn(phrase, admin)

    def test_project_workflows_match_script(self):
        script = read(ROOT / "scripts/github/setup_project.sh")
        admin = read(PROCESS / "ADMIN_SETUP.md")
        for name in ("Item added to project", "Item closed", "Pull request merged", "Item reopened",
                     "Auto-add to project"):
            self.assertIn(name, script)
            self.assertIn(name, admin)

    def test_protected_checks_match_script(self):
        script = read(ROOT / "scripts/github/protect_branches.sh")
        sdlc = read(PROCESS / "SDLC.md")
        for check in ("pr-check", "sdlc-scripts", "secret-scan", "mockup-scan"):
            self.assertIn(f'"{check}"', script)
            self.assertIn(f"`{check}`", sdlc)


class ReposTableTest(unittest.TestCase):
    def test_repos_table_matches_manifest(self):
        rows = table_rows(read(PROCESS / "REPOS.md"), "Key")
        by_key = {row[0].strip("`"): row for row in rows}
        repos = manifest_repos()
        self.assertEqual(sorted(by_key), sorted(r["key"] for r in repos))
        for repo in repos:
            key, name, area, stack, branch, verify, notes = by_key[repo["key"]]
            self.assertEqual(name, f"[{repo['name']}](https://github.com/Medtronic-LABS/{repo['name']})")
            self.assertEqual(area, repo["area"])
            self.assertEqual(stack, repo["stack"])
            self.assertEqual(branch, f"`{repo['integration_branch']}`")
            commands = [repo["verify"][k] for k in ("test", "lint", "build")]
            expected = " / ".join(f"`{c}`" if c else "none" for c in commands)
            self.assertEqual(verify, expected, repo["key"])
            self.assertEqual(notes.replace("`", ""), repo.get("notes", "").replace("`", ""), repo["key"])

    def test_claude_md_workspace_map_matches_manifest(self):
        claude = read(ROOT / "CLAUDE.md")
        for repo in manifest_repos():
            self.assertIn(f"| `{repo['key']}` | `repos/{repo['name']}` |", claude)

    def test_wiki_repos_page_lists_every_repo(self):
        page = read(WIKI / "Repos-and-Areas.md")
        for repo in manifest_repos():
            self.assertIn(f"https://github.com/Medtronic-LABS/{repo['name']}", page)


class ClaudeMdTest(unittest.TestCase):
    def test_lists_every_skill_and_agent(self):
        claude = read(ROOT / "CLAUDE.md")
        names = names_in(ROOT / ".claude/skills", "*/SKILL.md") + names_in(ROOT / ".claude/agents", "*.md")
        self.assertTrue(names)
        for name in names:
            self.assertIn(f"`{name}`", claude, f"CLAUDE.md does not list {name}")

    def test_key_rules_present(self):
        claude = read(ROOT / "CLAUDE.md")
        for phrase in ("Start Claude from the leapwell root", "/lw-setup", "docs/process/SDLC.md", "## Human-only gates",
                       "## Privacy rules", "## Workspace map", "## Ticket model", "repos.json", "public"):
            self.assertIn(phrase, claude)

    def test_engineering_standards_section(self):
        claude = read(ROOT / "CLAUDE.md")
        self.assertIn("## Engineering Design Standards", claude)
        section = claude[claude.index("## Engineering Design Standards"):]
        for label in STANDARDS_LABELS:
            self.assertIn(f"**{label}.**", section)
        self.assertIn("repos/uhis_lf_mobile/lib/core/constants/app_strings.dart", section)
        self.assertNotIn("design/flutter-standards.md", section)

    def test_readme_links_docs_and_setup(self):
        readme = read(ROOT / "README.md")
        for phrase in ("/lw-setup", "docs/process/SDLC.md", "docs/process/TICKETS.md", "claude", "Rollout status"):
            self.assertIn(phrase, readme)


class WikiAndMockupsTest(unittest.TestCase):
    def test_wiki_pages_exist_and_are_short(self):
        for page in WIKI_PAGES:
            path = WIKI / f"{page}.md"
            self.assertTrue(path.is_file(), f"wiki/{page}.md missing")
            self.assertLessEqual(len(read(path).splitlines()), 60, page)
        self.assertEqual(sorted(p.stem for p in WIKI.glob("*.md")), sorted(WIKI_PAGES))

    def test_feature_pages_have_required_sections(self):
        for page in FEATURE_PAGES:
            text = read(WIKI / f"{page}.md")
            for heading in ("## What it is", "## Who uses it", "## Repos", "## Mockups", "## Open questions"):
                self.assertIn(heading, text, f"{page} lacks {heading}")
            self.assertIn("https://github.com/Medtronic-LABS/", text)
            self.assertIn("/mockups", text)
            self.assertIn("/discussions", text)

    def test_home_links_every_page(self):
        home = read(WIKI / "Home.md")
        for page in WIKI_PAGES:
            if page != "Home":
                self.assertIn(f"({page})", home, f"Home does not link {page}")

    def test_mockups_docs(self):
        readme = read(MOCKUPS / "README.md")
        for phrase in ("mockups/<feature-slug>/", "HTML, PNG, SVG, PDF", "Fake data only", "mockup-scan",
                       "scan_text.py", "_template/README.md", "PR"):
            self.assertIn(phrase, readme)
        template = read(MOCKUPS / "_template" / "README.md")
        for phrase in ("Medtronic-LABS/leapwell#", "Fake data only"):
            self.assertIn(phrase, template)


class PublicTextTest(unittest.TestCase):
    def test_no_live_jira_process(self):
        for path in public_text_files():
            self.assertIsNone(JIRA_KEY_RE.search(read(path)), f"{path.name} contains a Jira key")

    def test_no_sensitive_data(self):
        for path in public_text_files():
            for number, line in enumerate(read(path).splitlines(), start=1):
                self.assertEqual(find_sensitive(line), [], f"{path.relative_to(ROOT)}:{number}")

    def test_only_allowed_urls(self):
        for path in public_text_files():
            for url in URL_RE.findall(read(path)):
                self.assertTrue(url.startswith(ALLOWED_URL_PREFIXES), f"{path.relative_to(ROOT)}: {url}")

    def test_relative_links_resolve(self):
        for path in public_text_files():
            for target in LINK_RE.findall(read(path)):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                candidates = [path.parent / relative]
                if path.parent == WIKI:
                    candidates.append(WIKI / f"{relative}.md")
                self.assertTrue(any(c.exists() for c in candidates), f"{path.relative_to(ROOT)}: broken link {target}")


if __name__ == "__main__":
    unittest.main()
