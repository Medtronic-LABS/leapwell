"""Tests for scripts.sync.sync_repos (temp git repos, no network)."""

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.sdlc import repos
from scripts.sync import sync_repos
from scripts.sync.sync_repos import SyncError, sync_repo

MANIFEST = repos.load()
MOBILE = MANIFEST.by_key("mobile")
REF = "v1"


def git(clone, *args):
    done = subprocess.run(["git", *args], cwd=clone, capture_output=True, text=True, check=True)
    return done.stdout


def make_clone(root: Path, files=None, name="uhis_lf_mobile") -> Path:
    clone = root / name
    clone.mkdir(parents=True)
    git(clone, "init", "-q", "-b", "develop")
    git(clone, "config", "user.email", "t@example.com")
    git(clone, "config", "user.name", "T")
    git(clone, "config", "commit.gpgsign", "false")
    git(clone, "config", "core.hooksPath", "/dev/null")
    (clone / "README.md").write_text("hi\n")
    for rel, content in (files or {}).items():
        path = clone / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "init")
    return clone


class SyncCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def sync(self, clone, apply=True, repo=MOBILE):
        return sync_repo(clone, repo, MANIFEST, REF, apply)

    def head(self, clone):
        return git(clone, "rev-parse", "HEAD").strip()


class TestApply(SyncCase):
    def test_first_run_commits_on_sync_branch_second_run_is_noop(self):
        clone = make_clone(self.root)
        plan = self.sync(clone)
        self.assertTrue(plan.changed)
        self.assertEqual(git(clone, "rev-parse", "--abbrev-ref", "HEAD").strip(), "chore/leapwell-sync")
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        self.assertIn("chore(sync)", git(clone, "log", "-1", "--format=%s"))
        for rel in (
            ".github/workflows/lw-pr-check.yml",
            ".github/workflows/lw-secret-scan.yml",
            ".github/workflows/lw-close-on-merge.yml",
            ".github/pull_request_template.md",
            ".github/CODEOWNERS",
            "CLAUDE.md",
            ".github/ISSUE_TEMPLATE/config.yml",
        ):
            self.assertTrue((clone / rel).is_file(), rel)
        before = self.head(clone)
        self.assertFalse(self.sync(clone).changed)
        self.assertEqual(self.head(clone), before)

    def test_noop_on_clean_repo_does_not_create_branch(self):
        clone = make_clone(self.root)
        self.sync(clone)
        git(clone, "checkout", "-q", "develop")
        git(clone, "merge", "-q", "chore/leapwell-sync")
        git(clone, "branch", "-q", "-d", "chore/leapwell-sync")
        self.assertFalse(self.sync(clone).changed)
        self.assertEqual(git(clone, "rev-parse", "--abbrev-ref", "HEAD").strip(), "develop")

    def test_placeholders_are_all_rendered(self):
        clone = make_clone(self.root)
        self.sync(clone)
        close = (clone / ".github/workflows/lw-close-on-merge.yml").read_text()
        self.assertIn("'develop'", close)
        self.assertIn("ref: v1", close)
        self.assertIn("repository: Medtronic-LABS/leapwell", close)
        for path in (clone / ".github").rglob("*"):
            if path.is_file():
                for name in ("org", "tracker", "repo", "integration_branch", "leapwell_ref"):
                    self.assertNotIn("{{" + name + "}}", path.read_text(), str(path))

    def test_gh_expressions_survive_rendering(self):
        clone = make_clone(self.root)
        self.sync(clone)
        self.assertIn(
            "${{ github.event.pull_request.number }}", (clone / ".github/workflows/lw-pr-check.yml").read_text()
        )


class TestMarkedSections(SyncCase):
    def test_claude_md_without_markers_is_appended_and_replaced_later_byte_exact(self):
        original = "# Repo\n\nline one\r\n\ttabbed  \n\nlast line no newline"
        clone = make_clone(self.root, {"CLAUDE.md": original})
        self.sync(clone)
        text = (clone / "CLAUDE.md").read_text(newline="")
        self.assertTrue(text.startswith(original))
        self.assertIn("<!-- leapwell:begin -->", text)

        # Hand-edit text around the section, then re-sync with a new ref: only the section changes.
        before, _, rest = text.partition("<!-- leapwell:begin -->")
        _, _, after = rest.partition("<!-- leapwell:end -->")
        edited = "TOP\n" + before + "<!-- leapwell:begin -->\nstale\n<!-- leapwell:end -->" + after + "\nBOTTOM\n"
        (clone / "CLAUDE.md").write_text(edited, newline="")
        git(clone, "commit", "-q", "-am", "edit")
        sync_repo(clone, MOBILE, MANIFEST, "v2", True)
        new = (clone / "CLAUDE.md").read_text(newline="")
        self.assertNotIn("stale", new)
        self.assertTrue(new.startswith("TOP\n" + before))
        self.assertTrue(new.endswith(after + "\nBOTTOM\n"))

    def test_replace_marked_leaves_other_bytes_identical(self):
        markers = sync_repos.MD_MARKERS
        existing = "a\n<!-- leapwell:begin -->\nold\n<!-- leapwell:end -->\nz"
        out = sync_repos.replace_marked(existing, "<!-- leapwell:begin -->\nnew\n<!-- leapwell:end -->\n", markers)
        self.assertEqual(out, "a\n<!-- leapwell:begin -->\nnew\n<!-- leapwell:end -->\nz")
        self.assertIsNone(sync_repos.replace_marked("nothing", "x", markers))

    def test_issue_config_without_markers_needs_manual_merge_and_is_untouched(self):
        original = "blank_issues_enabled: false\ncontact_links:\n  - name: x\n    url: https://e.com\n    about: y\n"
        clone = make_clone(self.root, {".github/ISSUE_TEMPLATE/config.yml": original})
        plan = self.sync(clone)
        self.assertEqual((clone / ".github/ISSUE_TEMPLATE/config.yml").read_text(), original)
        self.assertTrue(any("needs manual merge" in n for n in plan.notes))
        self.assertTrue(plan.changed)

    def test_issue_config_with_markers_replaces_only_between(self):
        existing = (
            "blank_issues_enabled: false\ncontact_links:\n  - name: keep\n    url: https://e.com\n    about: k\n"
            "  # leapwell:begin\n  - name: stale\n  # leapwell:end\n"
        )
        clone = make_clone(self.root, {".github/ISSUE_TEMPLATE/config.yml": existing})
        self.sync(clone)
        new = (clone / ".github/ISSUE_TEMPLATE/config.yml").read_text()
        self.assertTrue(new.startswith(existing.split("  # leapwell:begin")[0]))
        self.assertNotIn("stale", new)
        self.assertIn("issues/new/choose", new)
        self.assertEqual(new.count("# leapwell:begin"), 1)


class TestSafety(SyncCase):
    def test_existing_codeowners_untouched(self):
        clone = make_clone(self.root, {".github/CODEOWNERS": "* @someone\n"})
        plan = self.sync(clone)
        self.assertEqual((clone / ".github/CODEOWNERS").read_text(), "* @someone\n")
        self.assertTrue(any("CODEOWNERS" in n for n in plan.notes))

    def test_existing_pr_template_in_other_case_is_updated_in_place(self):
        clone = make_clone(self.root, {".github/PULL_REQUEST_TEMPLATE.md": "old\n"})
        plan = self.sync(clone)
        self.assertIn(".github/PULL_REQUEST_TEMPLATE.md", plan.writes)
        self.assertNotIn(".github/pull_request_template.md", plan.writes)
        tracked = git(clone, "ls-files", ".github").split()
        self.assertEqual(
            [p for p in tracked if p.lower().endswith("pull_request_template.md")], [".github/PULL_REQUEST_TEMPLATE.md"]
        )
        self.assertEqual(git(clone, "status", "--porcelain"), "")

    def test_pr_template_at_root_or_docs_is_updated_there(self):
        for rel in ("pull_request_template.md", "docs/Pull_Request_Template.md"):
            with self.subTest(rel=rel):
                clone = make_clone(self.root / rel.replace("/", "_"), {rel: "old\n"})
                plan = self.sync(clone)
                self.assertIn(rel, plan.writes)
                self.assertFalse(
                    (clone / ".github").exists()
                    and any(p.name.lower() == "pull_request_template.md" for p in (clone / ".github").iterdir())
                )

    def test_codeowners_at_root_or_docs_is_left_untouched(self):
        for rel in ("CODEOWNERS", "docs/CODEOWNERS"):
            with self.subTest(rel=rel):
                clone = make_clone(self.root / rel.replace("/", "_"), {rel: "* @someone\n"})
                plan = self.sync(clone)
                self.assertEqual((clone / rel).read_text(), "* @someone\n")
                self.assertFalse((clone / ".github/CODEOWNERS").exists())
                self.assertTrue(any("CODEOWNERS" in n for n in plan.notes))

    def test_claude_md_in_other_case_gets_the_section(self):
        clone = make_clone(self.root, {"claude.md": "# Own\n"})
        plan = self.sync(clone)
        self.assertIn("claude.md", plan.writes)
        self.assertNotIn("CLAUDE.md", plan.writes)

    def test_dirty_clone_refused(self):
        clone = make_clone(self.root)
        (clone / "README.md").write_text("changed\n")
        with self.assertRaises(SyncError):
            self.sync(clone)
        self.assertFalse((clone / ".github").exists())

    def test_untracked_file_counts_as_dirty(self):
        clone = make_clone(self.root)
        (clone / "scratch.txt").write_text("x")
        with self.assertRaises(SyncError):
            self.sync(clone)

    def test_missing_clone_refused(self):
        with self.assertRaisesRegex(SyncError, "not cloned"):
            self.sync(self.root / "nope")

    def test_dry_run_writes_nothing(self):
        clone = make_clone(self.root)
        before = self.head(clone)
        plan = self.sync(clone, apply=False)
        self.assertTrue(plan.changed)
        self.assertTrue(plan.diffs)
        self.assertFalse((clone / ".github").exists())
        self.assertEqual(self.head(clone), before)
        self.assertEqual(git(clone, "rev-parse", "--abbrev-ref", "HEAD").strip(), "develop")
        self.assertEqual(git(clone, "status", "--porcelain"), "")

    def test_never_pushes(self):
        source = inspect_source()
        self.assertNotIn('"push"', source)


def inspect_source() -> str:
    return Path(sync_repos.__file__).read_text(encoding="utf-8")


class TestMain(SyncCase):
    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sync_repos.main(list(argv))
        return code, out.getvalue()

    def manifest_env(self):
        data = {
            "org": "Medtronic-LABS",
            "tracker": "leapwell",
            "project": 4,
            "repos": [
                {
                    "key": k,
                    "name": n,
                    "area": "a",
                    "stack": "s",
                    "integration_branch": "develop",
                    "protected_branches": ["develop"],
                    "verify": {"test": "", "lint": "", "build": ""},
                }
                for k, n in (("a", "alpha"), ("b", "beta"), ("c", "gamma"))
            ],
        }
        path = self.root / "repos.json"
        path.write_text(json.dumps(data))
        return mock.patch.dict(os.environ, {"LW_REPOS_JSON": str(path)})

    def test_refused_and_missing_repos_do_not_stop_others_and_exit_1(self):
        ws = self.root / "ws"
        dirty = make_clone(ws, name="alpha")
        (dirty / "README.md").write_text("dirty\n")
        make_clone(ws, name="beta")
        with self.manifest_env():
            code, out = self.run_main("--all", "--apply", "--workspace", str(ws))
        self.assertEqual(code, 1)
        self.assertIn("refused: working tree is dirty", out)
        self.assertIn("not cloned — run /lw-setup", out)
        self.assertTrue((ws / "beta/.github/workflows/lw-pr-check.yml").is_file())
        self.assertFalse((ws / "alpha/.github").exists())

    def test_dry_run_prints_diff_and_exits_0(self):
        ws = self.root / "ws"
        make_clone(ws, name="alpha")
        with self.manifest_env():
            code, out = self.run_main("--repo", "a", "--workspace", str(ws))
        self.assertEqual(code, 0)
        self.assertIn("+++ b/.github/workflows/lw-pr-check.yml", out)

    def test_unknown_repo_key_exits_1(self):
        with self.manifest_env(), contextlib.redirect_stderr(io.StringIO()):
            code, _ = self.run_main("--repo", "zzz", "--workspace", str(self.root))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
