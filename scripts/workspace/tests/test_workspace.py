import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.workspace import doctor

ROOT = Path(__file__).resolve().parents[3]
HOOKS = ROOT / ".githooks"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(cwd, *args, check=True):
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=check)


def entry(key, name, area="Mobile app", branch="develop"):
    return {"key": key, "name": name, "area": area, "stack": "x", "integration_branch": branch,
            "protected_branches": [branch], "verify": {"test": "t", "lint": "l", "build": "b"}}


class DoctorTests(unittest.TestCase):
    def test_required_tools_by_area(self):
        tools = doctor.required_tools(["Mobile app", "Micro-coaching"])
        for tool in ("git", "gh", "python3", "flutter", "java", "docker", "node", "npm"):
            self.assertIn(tool, tools)
        self.assertEqual(doctor.required_tools(["Frappe apps"]).get("flutter"), None)

    def test_missing_and_ok(self):
        rows = doctor.check(["Frappe apps"], which=lambda t: None if t == "docker" else "/bin/" + t,
                            run=lambda c: 0, python_version=(3, 12))
        status = {tool: st for tool, st, _ in rows}
        self.assertEqual(status["docker"], "MISSING")
        self.assertEqual(status["git"], "ok")

    def test_old_python_and_gh_auth_fail(self):
        rows = doctor.check([], which=lambda t: "/bin/" + t, run=lambda c: 1, python_version=(3, 9))
        status = {tool: st for tool, st, _ in rows}
        self.assertEqual(status["python3"], "FAIL")
        self.assertEqual(status["gh"], "FAIL")


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.remotes = self.tmp / "remotes"
        self.remotes.mkdir()
        self.make_remote("alpha", {"README": "a\n"})

    def make_remote(self, name, files, branch="develop"):
        work = self.tmp / "seed" / name
        work.mkdir(parents=True)
        git(work, "init", "-q", "-b", branch)
        for rel, text in files.items():
            path = work / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "seed")
        git(self.tmp, "clone", "-q", "--bare", str(work), str(self.remotes / f"{name}.git"))

    def manifest(self, *entries):
        path = self.tmp / "repos.json"
        path.write_text(json.dumps({"org": "o", "tracker": "t", "project": 1, "repos": list(entries)}))
        return path


class SetupTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.lw = self.tmp / "lw"
        shutil.copytree(ROOT / "scripts", self.lw / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "tests"))
        shutil.copytree(HOOKS, self.lw / ".githooks")
        shutil.copy(ROOT / "repos.json", self.lw / "repos.json")

    def clone_dir(self, name):
        return self.lw / "repos" / name

    def run_setup(self, manifest, *args):
        env = {**os.environ, "LW_REPOS_JSON": str(manifest), "LW_CLONE_BASE": f"file://{self.remotes}/"}
        return subprocess.run(["bash", str(self.lw / "scripts/workspace/setup.sh"), *args],
                              cwd=self.lw, env=env, capture_output=True, text=True)

    def test_help_and_no_clone_touch_nothing(self):
        manifest = self.manifest(entry("a", "alpha"))
        self.assertEqual(self.run_setup(manifest, "--help").returncode, 0)
        done = self.run_setup(manifest, "--no-clone")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((self.lw / "repos").exists())

    def test_clone_sets_hooks_and_rerun_is_noop(self):
        manifest = self.manifest(entry("a", "alpha"))
        done = self.run_setup(manifest, "--only", "a")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        clone = self.clone_dir("alpha")
        self.assertTrue((clone / "README").exists())
        hooks = git(clone, "config", "core.hooksPath").stdout.strip()
        self.assertEqual(hooks, str(self.lw.resolve() / ".githooks"))
        head = git(clone, "rev-parse", "HEAD").stdout
        again = self.run_setup(manifest, "--only", "a")
        self.assertEqual(again.returncode, 0)
        self.assertIn("clean", again.stdout)
        self.assertEqual(git(clone, "rev-parse", "HEAD").stdout, head)

    def test_dirty_clone_untouched(self):
        manifest = self.manifest(entry("a", "alpha"))
        self.run_setup(manifest, "--only", "a")
        clone = self.clone_dir("alpha")
        (clone / "README").write_text("local edit\n")
        again = self.run_setup(manifest, "--only", "a")
        self.assertIn("DIRTY", again.stdout)
        self.assertEqual((clone / "README").read_text(), "local edit\n")

    def test_failed_clone_continues_and_strict_fails(self):
        manifest = self.manifest(entry("m", "missing"), entry("a", "alpha"))
        done = self.run_setup(manifest)
        self.assertEqual(done.returncode, 0)
        self.assertIn("clone FAILED", done.stdout)
        self.assertTrue((self.clone_dir("alpha") / "README").exists())
        self.assertEqual(self.run_setup(manifest, "--strict").returncode, 1)


class HookTests(WorkspaceCase):
    def clone_with_hooks(self, files=None):
        name = "beta"
        self.make_remote(name, files or {"README": "b\n"})
        clone = self.tmp / "work" / name
        git(self.tmp, "clone", "-q", str(self.remotes / f"{name}.git"), str(clone))
        git(clone, "config", "core.hooksPath", str(HOOKS))
        (clone / "f.txt").write_text("x\n")
        git(clone, "add", "f.txt")
        return clone

    def commit(self, clone, message):
        return git(clone, "commit", "-m", message, check=False)

    def test_bad_subject_rejected_from_clone(self):
        clone = self.clone_with_hooks()
        done = self.commit(clone, "did some stuff")
        self.assertNotEqual(done.returncode, 0)

    def test_good_subject_accepted_without_repo_hook(self):
        clone = self.clone_with_hooks()
        self.assertEqual(self.commit(clone, "feat(x): thing").returncode, 0)

    def test_chains_to_repo_hook_and_failure_fails_commit(self):
        clone = self.clone_with_hooks()
        hook = clone / ".githooks"
        hook.mkdir()
        marker = self.tmp / "ran"
        script = hook / "commit-msg"
        script.write_text(f'#!/bin/sh\necho "$1" > "{marker}"\nexit 0\n')
        script.chmod(0o755)
        self.assertEqual(self.commit(clone, "feat(x): thing").returncode, 0)
        self.assertTrue(marker.exists())

        (clone / "g.txt").write_text("y\n")
        git(clone, "add", "g.txt")
        script.write_text("#!/bin/sh\nexit 1\n")
        self.assertNotEqual(self.commit(clone, "feat(x): other").returncode, 0)

    def test_chains_to_git_dir_hook(self):
        clone = self.clone_with_hooks()
        script = clone / ".git" / "hooks" / "pre-commit"
        script.write_text("#!/bin/sh\nexit 1\n")
        script.chmod(0o755)
        self.assertNotEqual(self.commit(clone, "feat(x): thing").returncode, 0)

    def test_pre_commit_blocks_secret_file(self):
        clone = self.clone_with_hooks()
        (clone / "env.dev.json").write_text("{}\n")
        git(clone, "add", "-f", "env.dev.json")
        done = self.commit(clone, "feat(x): thing")
        self.assertNotEqual(done.returncode, 0)


@unittest.skipUnless(shutil.which("rg"), "ripgrep not installed")
class IgnoreFileTests(unittest.TestCase):
    def test_rg_searches_gitignored_repos(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        git(tmp, "init", "-q")
        (tmp / ".gitignore").write_text("/repos/\n")
        shutil.copy(ROOT / ".ignore", tmp / ".ignore")
        (tmp / "repos" / "x").mkdir(parents=True)
        (tmp / "repos" / "x" / "a.txt").write_text("hi\n")
        done = subprocess.run(["rg", "--files"], cwd=tmp, capture_output=True, text=True)
        self.assertIn("a.txt", done.stdout)


if __name__ == "__main__":
    unittest.main()
