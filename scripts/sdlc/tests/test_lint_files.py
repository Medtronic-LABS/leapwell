"""Tests for scripts.sdlc.lint_files (temp git repos, fake lint tools; no network)."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.sdlc import lint_files, repos
from scripts.sdlc.repos import LintRule

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_RULE = LintRule(files=("*.py",), run="fakelint")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def make_repo(root: Path, name="beta", files=None) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "T")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "core.hooksPath", "/dev/null")
    git(repo, "remote", "add", "origin", f"https://github.com/O/{name}.git")
    (repo / "README.md").write_text("hi\n")
    for rel, text in (files or {}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def fake_tool(bindir: Path, name="fakelint"):
    """A lint tool that fails when any given file contains BAD and records its arguments."""
    bindir.mkdir(parents=True, exist_ok=True)
    tool = bindir / name
    tool.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "$(dirname "$0")/calls"\n'
        'for f in "$@"; do case "$f" in -*) ;; *) grep -q BAD "$f" && { echo "$f: BAD"; exit 1; } ;; esac; done\n'
        "exit 0\n"
    )
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return bindir / "calls"


class TestSelect(unittest.TestCase):
    def test_globs_match_nested_paths_and_dotdirs(self):
        paths = ["a.py", "pkg/b.py", "c.dart", ".githooks/pre-commit", "x.sh", ".github/workflows/ci.yml"]
        self.assertEqual(lint_files.select(paths, ("*.py",)), ["a.py", "pkg/b.py"])
        self.assertEqual(lint_files.select(paths, ("*.sh", ".githooks/*")), [".githooks/pre-commit", "x.sh"])
        self.assertEqual(lint_files.select(paths, (".github/workflows/*.yml",)), [".github/workflows/ci.yml"])

    def test_remote_name(self):
        for url in ("https://github.com/O/beta.git", "git@github.com:O/beta.git", "https://github.com/O/beta"):
            self.assertEqual(lint_files.remote_repo_name(url), "beta", url)


class TestRulesFor(unittest.TestCase):
    def setUp(self):
        self.manifest = repos.Manifest(
            org="O",
            tracker="T",
            project=1,
            repos=(
                repos.Repo("b", "beta", "a", "s", "main", ("main",), {}, lint_rules=(PY_RULE,)),
                repos.Repo("c", "gamma", "a", "s", "main", ("main",), {}),
            ),
            hub_lint_rules=(LintRule(files=("*.sh",), run="shellcheck"),),
        )

    def test_hub_known_unknown(self):
        self.assertEqual(lint_files.rules_for(self.manifest, is_hub=True, name="x"), self.manifest.hub_lint_rules)
        self.assertEqual(lint_files.rules_for(self.manifest, is_hub=False, name="beta"), (PY_RULE,))
        self.assertEqual(lint_files.rules_for(self.manifest, is_hub=False, name="gamma"), ())
        self.assertEqual(lint_files.rules_for(self.manifest, is_hub=False, name="unknown"), ())


class TestRunRules(unittest.TestCase):
    def test_missing_tool_blocks_with_install_hint(self):
        problems = lint_files.run_rules((PY_RULE,), ["a.py"], Path("."), which=lambda _: None)
        self.assertEqual(len(problems), 1)
        self.assertIn("fakelint", problems[0])
        self.assertIn("not installed", problems[0])

    def test_no_matching_files_skips_tool_entirely(self):
        problems = lint_files.run_rules((PY_RULE,), ["a.dart"], Path("."), which=lambda _: None)
        self.assertEqual(problems, [])

    def test_failing_command_reported_and_files_appended(self):
        calls = []

        def runner(cmd, cwd):
            calls.append(cmd)
            return 1

        problems = lint_files.run_rules(
            (LintRule(files=("*.py",), run="ruff check --isolated"),),
            ["a.py", "b.py"],
            Path("."),
            which=lambda t: f"/bin/{t}",
            runner=runner,
        )
        self.assertEqual(calls, [["ruff", "check", "--isolated", "a.py", "b.py"]])
        self.assertEqual(len(problems), 1)
        self.assertIn("ruff check --isolated", problems[0])

    def test_many_files_are_chunked(self):
        calls = []
        lint_files.run_rules(
            (PY_RULE,),
            [f"f{i}.py" for i in range(lint_files.CHUNK + 5)],
            Path("."),
            which=lambda t: t,
            runner=lambda cmd, cwd: calls.append(cmd) or 0,
        )
        self.assertEqual([len(c) - 1 for c in calls], [lint_files.CHUNK, 5])


class TestCli(unittest.TestCase):
    """End to end through git: staged and base modes against a temp repo with a fake tool on PATH."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.calls = fake_tool(self.root / "bin")
        manifest = self.root / "repos.json"
        manifest.write_text(
            '{"org": "O", "tracker": "T", "project": 1, "repos": [{"key": "b", "name": "beta", "area": "a",'
            ' "stack": "s", "integration_branch": "main", "protected_branches": ["main"],'
            ' "verify": {"test": "t", "lint": "", "build": ""},'
            ' "lint_rules": [{"files": ["*.py"], "run": "fakelint --strict"}]}]}'
        )
        self.env = {**os.environ, "LW_REPOS_JSON": str(manifest), "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}"}

    def cli(self, repo, *args):
        script = REPO_ROOT / "scripts/sdlc/lint_files.py"
        return subprocess.run(
            [sys.executable, str(script), *args], cwd=repo, env=self.env, capture_output=True, text=True
        )

    def test_staged_lints_only_staged_matching_files(self):
        repo = make_repo(self.root, files={"old.py": "BAD\n"})
        (repo / "new.py").write_text("ok\n")
        (repo / "notes.md").write_text("BAD\n")
        git(repo, "add", "new.py", "notes.md")
        done = self.cli(repo, "--staged")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls.read_text().split(), ["--strict", "new.py"])

    def test_staged_failure_blocks(self):
        repo = make_repo(self.root)
        (repo / "bad.py").write_text("BAD\n")
        git(repo, "add", "bad.py")
        done = self.cli(repo, "--staged")
        self.assertEqual(done.returncode, 1)
        self.assertIn("bad.py: BAD", done.stdout + done.stderr)

    def test_deleted_files_are_not_linted(self):
        repo = make_repo(self.root, files={"gone.py": "BAD\n"})
        git(repo, "rm", "-q", "gone.py")
        self.assertEqual(self.cli(repo, "--staged").returncode, 0)

    def test_repo_with_own_precommit_setup_is_skipped_when_staged(self):
        for own in (".pre-commit-config.yaml", ".husky/pre-commit"):
            with self.subTest(own=own):
                repo = make_repo(self.root / own.replace("/", "_"), files={own: "x\n"})
                (repo / "bad.py").write_text("BAD\n")
                git(repo, "add", "bad.py")
                done = self.cli(repo, "--staged")
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn("own pre-commit", done.stdout + done.stderr)

    def test_base_mode_lints_changes_since_base_even_with_own_setup(self):
        repo = make_repo(self.root, files={".pre-commit-config.yaml": "x\n", "old.py": "BAD\n"})
        git(repo, "switch", "-q", "-c", "feat/1-x")
        (repo / "new.py").write_text("BAD\n")
        git(repo, "add", "new.py")
        git(repo, "commit", "-q", "-m", "x")
        done = self.cli(repo, "--base", "main")
        self.assertEqual(done.returncode, 1)
        self.assertIn("new.py", done.stdout + done.stderr)
        self.assertNotIn("old.py", self.calls.read_text())

    def test_unknown_repo_passes(self):
        repo = make_repo(self.root, name="stranger")
        (repo / "bad.py").write_text("BAD\n")
        git(repo, "add", "bad.py")
        self.assertEqual(self.cli(repo, "--staged").returncode, 0)


if __name__ == "__main__":
    unittest.main()
