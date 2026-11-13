"""Tests for scripts/github/*.sh: dry-run by default, nothing mutating without --apply."""

import json
import os
import stat
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.sdlc import repos

ROOT = Path(__file__).resolve().parents[3]
GH_DIR = ROOT / "scripts" / "github"
ALL = [
    "sync_labels.sh",
    "setup_project.sh",
    "setup_discussions.sh",
    "publish_wiki.sh",
    "protect_branches.sh",
    "package_skill.sh",
]
# Scripts that print a gh command in dry-run (publish_wiki / package_skill need other inputs).
GH_DRY_RUN = ["sync_labels.sh", "setup_project.sh", "setup_discussions.sh", "protect_branches.sh"]


def make_fake_gh(directory: Path, log: Path, exit_code: int) -> None:
    fake = directory / "gh"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit {exit_code}\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env=dict(
            os.environ,
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL="t@example.com",
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@example.com",
        ),
    )


class AdminScriptsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.calls = base / "gh_calls.log"
        bin_dir = base / "bin"
        bin_dir.mkdir()
        make_fake_gh(bin_dir, cls.calls, 99)
        cls.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.calls.unlink(missing_ok=True)

    def run_script(self, name, *args, env=None):
        return subprocess.run(
            ["bash", str(GH_DIR / name), *args], capture_output=True, text=True, env=env or self.env, cwd=ROOT
        )

    def test_scripts_exist_and_executable(self):
        for name in ALL + ["lib.sh"]:
            self.assertTrue((GH_DIR / name).is_file(), name)
        for name in ALL:
            self.assertTrue(os.access(GH_DIR / name, os.X_OK), name)

    def test_help_exits_zero(self):
        for name in ALL:
            r = self.run_script(name, "--help")
            self.assertEqual(r.returncode, 0, name + r.stderr)
            self.assertIn("Usage", r.stdout)
        self.assertFalse(self.calls.exists())

    def test_dry_run_prints_gh_and_never_calls_it(self):
        for name in GH_DRY_RUN:
            r = self.run_script(name)
            self.assertEqual(r.returncode, 0, name + r.stderr)
            self.assertIn("gh", r.stdout, name)
            self.assertIn("DRY-RUN", r.stdout, name)
        self.assertFalse(self.calls.exists(), "gh was invoked during dry-run")

    def test_unknown_argument_is_rejected(self):
        for name in ALL:
            self.assertEqual(self.run_script(name, "--bogus").returncode, 2, name)

    def test_labels_dry_run_covers_every_label(self):
        out = self.run_script("sync_labels.sh").stdout
        self.assertIn("[dry-run] gh label create type:bug --color d73a4a", out)
        self.assertIn("--force", out)
        self.assertIn("good\\ first\\ issue", out)
        self.assertIn("status:routed", out)
        self.assertIn("--repo Medtronic-LABS/leapwell", out)
        self.assertNotIn("--repo Medtronic-LABS/uhis_lf_mobile", out)

    def test_labels_all_repos_covers_manifest(self):
        out = self.run_script("sync_labels.sh", "--all-repos").stdout
        for repo in repos.load().repos:
            self.assertIn(f"--repo Medtronic-LABS/{repo.name}", out)
        self.assertFalse(self.calls.exists())

    def test_labels_apply_runs_gh(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            make_fake_gh(bin_dir, log, 0)
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
            r = self.run_script("sync_labels.sh", "--apply", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            calls = log.read_text().splitlines()
            self.assertTrue(all(c.startswith("label create ") for c in calls))
            self.assertIn("label create status:triage", "\n".join(calls))

    def test_protection_values(self):
        out = self.run_script("protect_branches.sh").stdout
        for check in ["pr-check", "sdlc-scripts", "lint", "secret-scan", "mockup-scan"]:
            self.assertIn(f'"{check}"', out)
        self.assertIn("repos/Medtronic-LABS/leapwell/branches/main/protection", out)
        self.assertNotIn("develop", out)
        self.assertIn('"required_approving_review_count": 1', out)
        self.assertIn('"enforce_admins": false', out)
        self.assertIn('"allow_force_pushes": false', out)

    def test_protect_apply_puts_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            make_fake_gh(bin_dir, log, 0)
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
            r = self.run_script("protect_branches.sh", "--apply", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("api -X PUT repos/Medtronic-LABS/leapwell/branches/main/protection", log.read_text())

    def test_project_dry_run_content(self):
        out = self.run_script("setup_project.sh").stdout
        for word in ["P0\\,P1\\,P2\\,P3", "Triage", "QA", "Settings", "project link"]:
            self.assertIn(word, out)
        self.assertIn("Backlog", out)
        self.assertIn("In review", out)
        self.assertNotIn("--name Type", out, "native issue types replace the Type field")

    def test_project_never_mutates_status(self):
        out = self.run_script("setup_project.sh").stdout
        self.assertNotIn("--name Status", out)
        # The only field update is a rename; an option list in a mutation can wipe item values.
        self.assertEqual(out.count("updateProjectV2Field("), 1)
        self.assertNotIn("singleSelectOptions", out)
        self.assertIn("UI", out)

    def test_project_never_deletes_or_changes_existing_objects(self):
        out = self.run_script("setup_project.sh").stdout
        for forbidden in ("deleteProjectV2", "deleteIssueType", "updateIssueType", "archiveProjectV2Item"):
            self.assertNotIn(forbidden, out)

    def test_project_links_every_repo(self):
        out = self.run_script("setup_project.sh").stdout
        self.assertIn("--repo Medtronic-LABS/leapwell ", out)
        for repo in repos.load().repos:
            self.assertIn(f"project link 4 --owner Medtronic-LABS --repo Medtronic-LABS/{repo.name} ", out)

    def test_project_issue_types_and_views(self):
        out = self.run_script("setup_project.sh").stdout
        for name in ("name=Epic", "name=Story", "name=Subtask"):
            self.assertIn(name, out)
        self.assertEqual(out.count("createIssueType("), 3)
        views = {
            "Product\\ Backlog": "filter=is:open ",
            "Sprint\\ Planning": "filter=is:open\\ -type:Epic",
            "Active\\ Sprint": "filter=sprint:@current\\ -type:Epic",
            "Release\\ Roadmap": "filter=type:Epic",
            "My\\ Work": "filter=assignee:@me\\ is:open",
        }
        for name, view_filter in views.items():
            self.assertIn(f"name={name}", out)
            self.assertIn(view_filter, out)
        self.assertEqual(out.count("createProjectV2View("), 5)

    def test_project_sprints_are_back_to_back_fortnights(self):
        out = self.run_script("setup_project.sh").stdout
        body = out.split("gh api graphql --input - <<'JSON'\n", 1)[1].split("\nJSON\n", 1)[0]
        config = json.loads(body)["variables"]["input"]
        self.assertEqual((config["dataType"], config["name"]), ("ITERATION", "Sprint"))
        sprints = config["iterationConfiguration"]["iterations"]
        self.assertEqual(len(sprints), 12)
        self.assertEqual((sprints[0]["title"], sprints[0]["startDate"]), ("Sprint 01", "2026-11-16"))
        self.assertEqual((sprints[1]["title"], sprints[1]["startDate"]), ("Sprint 02", "2026-11-30"))
        self.assertTrue(all(s["duration"] == 14 for s in sprints))
        self.assertTrue(all(date.fromisoformat(s["startDate"]).weekday() == 0 for s in sprints), "Mondays")

    def test_project_sprint_settings_are_overridable(self):
        env = dict(self.env, SPRINT_START="2027-01-04", SPRINT_DAYS="21", SPRINT_COUNT="2")
        out = self.run_script("setup_project.sh", env=env).stdout
        self.assertIn('"startDate": "2027-01-25"', out)
        self.assertNotIn("Sprint 03", out)

    def test_project_story_points_is_a_rename_of_the_unused_estimate_field(self):
        out = self.run_script("setup_project.sh").stdout
        self.assertIn("name=Story\\ Points", out)
        self.assertIn("field=\\<Estimate-id\\>", out)

    def test_project_apply_reads_state_first_and_writes_with_gh(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            make_fake_gh(bin_dir, log, 0)
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
            r = self.run_script("setup_project.sh", "--apply", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            calls = log.read_text()
            self.assertIn("issueTypes(first: 50)", calls.split("project link", 1)[0], "state is read before any write")
            self.assertEqual(calls.count("project link 4"), 8)
            self.assertIn("createIssueType", calls)
            self.assertIn("api graphql --input -", calls)
            self.assertNotIn("singleSelectOptions", calls)

    def test_project_apply_continues_when_issue_types_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "gh"
            fake.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\ncase "$*" in *createIssueType*) exit 1 ;; esac\n')
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
            r = self.run_script("setup_project.sh", "--apply", env=env)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Not created: issue type(s) Epic Story Subtask", r.stderr)
            calls = log.read_text()
            self.assertIn("createProjectV2View", calls, "later steps still ran")
            self.assertIn("api graphql --input -", calls)

    def test_discussions_dry_run_lists_ui_steps(self):
        out = self.run_script("setup_discussions.sh").stdout
        for category in ["Ideas", "Field feedback", "Partner requests", "Q&A", "Announcements"]:
            self.assertIn(category, out)
        self.assertIn("discussionCategories", out)
        self.assertFalse(self.calls.exists())


class WikiAndPackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def run_script(self, name, *args, **env):
        return subprocess.run(
            ["bash", str(GH_DIR / name), *args], capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, **env)
        )

    def wiki_source(self):
        source = self.base / "wiki_src"
        source.mkdir()
        (source / "Home.md").write_text("# Home\n")
        return str(source)

    def bare_remote(self, with_content: bool) -> str:
        remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        if with_content:
            work = self.base / "seed"
            work.mkdir()
            git(work, "init", "-q")
            (work / "Old.md").write_text("old\n")
            git(work, "add", "-A")
            git(work, "commit", "-q", "-m", "seed")
            git(work, "push", "-q", str(remote), "HEAD")
        return str(remote)

    def test_wiki_missing_source_dir_is_clear_error(self):
        r = self.run_script(
            "publish_wiki.sh", WIKI_SOURCE_DIR=str(self.base / "nope"), WIKI_URL=str(self.base / "x.git")
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("No wiki pages found", r.stderr)

    def test_wiki_remote_missing_dry_run_exits_zero_apply_exits_one(self):
        env = dict(WIKI_SOURCE_DIR=self.wiki_source(), WIKI_URL=str(self.base / "missing.git"))
        dry = self.run_script("publish_wiki.sh", **env)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("does not exist yet or is not accessible", dry.stdout)
        self.assertIn("git said:", dry.stdout)
        self.assertIn("Create the first wiki page in the UI (Wiki -> Create the first page), then re-run", dry.stdout)
        applied = self.run_script("publish_wiki.sh", "--apply", **env)
        self.assertEqual(applied.returncode, 1)
        self.assertIn("Create the first wiki page in the UI", applied.stdout)

    def test_wiki_dry_run_never_pushes(self):
        remote = self.bare_remote(with_content=False)
        r = self.run_script("publish_wiki.sh", WIKI_SOURCE_DIR=self.wiki_source(), WIKI_URL=remote)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[dry-run] git push origin HEAD", r.stdout)
        heads = subprocess.run(["git", "for-each-ref"], cwd=remote, capture_output=True, text=True).stdout
        self.assertEqual(heads.strip(), "")

    def test_wiki_apply_pushes_pages(self):
        remote = self.bare_remote(with_content=False)
        r = self.run_script("publish_wiki.sh", "--apply", WIKI_SOURCE_DIR=self.wiki_source(), WIKI_URL=remote)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=remote, capture_output=True, text=True
        ).stdout.split()
        self.assertEqual(files, ["Home.md"])

    def test_wiki_non_empty_refused_without_force(self):
        remote = self.bare_remote(with_content=True)
        env = dict(WIKI_SOURCE_DIR=self.wiki_source(), WIKI_URL=remote)
        refused = self.run_script("publish_wiki.sh", "--apply", **env)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("Refusing", refused.stderr)
        forced = self.run_script("publish_wiki.sh", "--apply", "--force", **env)
        self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
        files = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=remote, capture_output=True, text=True
        ).stdout.split()
        self.assertEqual(sorted(files), ["Home.md", "Old.md"])

    def test_package_skill_missing_dir_exits_one(self):
        skill = ROOT / ".claude" / "skills" / "lw-ticket"
        if skill.exists():
            self.skipTest("lw-ticket skill exists; missing-dir case not reproducible")
        r = self.run_script("package_skill.sh")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Skill folder not found", r.stderr)


if __name__ == "__main__":
    unittest.main()
