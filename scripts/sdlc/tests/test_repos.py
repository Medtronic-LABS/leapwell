"""Tests for scripts.sdlc.repos and the real repos.json."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.sdlc import repos
from scripts.sdlc.patterns import TRACKER_SLUG

EXPECTED_KEYS = ["mobile", "core", "shukhee", "ai", "coaching", "coaching-android", "coaching-dashboard"]
INTEGRATION = {
    "mobile": "develop",
    "core": "main",
    "shukhee": "main",
    "ai": "develop",
    "coaching": "leapwell-main",
    "coaching-android": "leapwell-main",
    "coaching-dashboard": "leapwell-main",
}


def good_entry(**over):
    entry = {
        "key": "k",
        "name": "n",
        "area": "a",
        "stack": "s",
        "integration_branch": "main",
        "protected_branches": ["main"],
        "verify": {"test": "t", "lint": "l", "build": "b"},
    }
    entry.update(over)
    return entry


def manifest(*entries):
    return {"org": "O", "tracker": "T", "project": 4, "repos": list(entries)}


class TestRealManifest(unittest.TestCase):
    def setUp(self):
        with mock.patch.dict(os.environ):
            os.environ.pop(repos.ENV_OVERRIDE, None)
            self.manifest = repos.load()

    def test_seven_repos_in_order(self):
        self.assertEqual([r.key for r in self.manifest.repos], EXPECTED_KEYS)

    def test_unique_keys_and_names(self):
        self.assertEqual(len({r.key for r in self.manifest.repos}), 7)
        self.assertEqual(len({r.name for r in self.manifest.repos}), 7)

    def test_integration_branches(self):
        self.assertEqual({r.key: r.integration_branch for r in self.manifest.repos}, INTEGRATION)

    def test_protected_contains_integration_and_main_without_duplicates(self):
        for repo in self.manifest.repos:
            self.assertIn(repo.integration_branch, repo.protected_branches, repo.key)
            self.assertIn("main", repo.protected_branches, repo.key)
            self.assertEqual(len(repo.protected_branches), len(set(repo.protected_branches)), repo.key)

    def test_protected_union(self):
        self.assertEqual(self.manifest.protected_branches(), {"main", "develop", "leapwell-main"})

    def test_tracker_slug_matches_patterns_constant(self):
        self.assertEqual(self.manifest.tracker_slug, "Medtronic-LABS/leapwell")
        self.assertEqual(self.manifest.tracker_slug, TRACKER_SLUG)
        self.assertEqual(self.manifest.project, 4)

    def test_lookups(self):
        self.assertEqual(self.manifest.by_key("ai").name, "leapfrog-ai-service")
        self.assertEqual(self.manifest.by_name("spice-coaching").key, "coaching")
        with self.assertRaises(KeyError):
            self.manifest.by_key("nope")

    def test_commands_are_runnable_and_notes_hold_prose(self):
        for repo in self.manifest.repos:
            self.assertIsInstance(repo.notes, str)
            for command in repo.verify.values():
                self.assertNotIn("(", command, repo.key)
        self.assertIn("{site}", self.manifest.by_key("core").verify["test"])
        self.assertIn("frappe env", self.manifest.by_key("core").notes)

    def test_every_repo_has_verify_commands(self):
        for repo in self.manifest.repos:
            self.assertEqual(set(repo.verify), {"test", "lint", "build"}, repo.key)
            self.assertTrue(repo.verify["test"], repo.key)

    def test_lint_rules_lint_only_never_reformat_whole_files(self):
        runs = {key: [r.run for r in self.manifest.by_key(key).lint_rules] for key in EXPECTED_KEYS}
        self.assertEqual(runs["mobile"], ["dart analyze"])
        for key in ("core", "shukhee", "coaching"):
            self.assertEqual(runs[key], ["ruff check"], key)
        self.assertEqual(runs["ai"], ["ruff check --isolated"])
        self.assertEqual(runs["coaching-android"], [])
        self.assertEqual(runs["coaching-dashboard"], ["npx --no eslint", "npx --no prettier --check"])
        for key in EXPECTED_KEYS:
            self.assertFalse(any("--fix" in r or "--write" in r for r in runs[key]), key)

    def test_hub_lint_rules_cover_python_shell_and_workflows(self):
        runs = {r.run: r.files for r in self.manifest.hub_lint_rules}
        self.assertEqual(runs["ruff check"], ("*.py",))
        self.assertEqual(runs["ruff format --check"], ("*.py",))
        self.assertIn(".githooks/*", runs["shellcheck -S warning -x"])
        self.assertEqual(runs["actionlint"], (".github/workflows/*.yml",))


class TestValidation(unittest.TestCase):
    def test_good_manifest_parses(self):
        self.assertEqual(repos.parse(manifest(good_entry())).tracker_slug, "O/T")

    def test_missing_top_key(self):
        with self.assertRaisesRegex(ValueError, "'repos'"):
            repos.parse({"org": "O", "tracker": "T", "project": 4})

    def test_bad_entry_named_in_error(self):
        for bad, needle in [
            (good_entry(key="broken", name=""), r"broken.*'name'"),
            (good_entry(key="broken", integration_branch=None), r"broken.*integration_branch"),
            (good_entry(key="broken", protected_branches=[]), r"broken.*protected_branches"),
            (good_entry(key="broken", verify={"test": "t"}), r"broken.*verify"),
        ]:
            with self.assertRaisesRegex(ValueError, needle):
                repos.parse(manifest(good_entry(key="ok"), bad))

    def test_lint_rules_parse_and_default_empty(self):
        rule = {"files": ["*.py"], "run": "ruff check"}
        parsed = repos.parse(
            {**manifest(good_entry(lint_rules=[rule]), good_entry(key="k2", name="n2")), "hub_lint_rules": [rule]}
        )
        self.assertEqual(parsed.by_key("k").lint_rules, (repos.LintRule(files=("*.py",), run="ruff check"),))
        self.assertEqual(parsed.by_key("k2").lint_rules, ())
        self.assertEqual(parsed.hub_lint_rules, (repos.LintRule(files=("*.py",), run="ruff check"),))
        self.assertEqual(repos.parse(manifest(good_entry())).hub_lint_rules, ())

    def test_bad_lint_rules_named_in_error(self):
        for bad in (
            [{"files": [], "run": "x"}],
            [{"files": ["*.py"], "run": ""}],
            [{"files": "*.py", "run": "x"}],
            "ruff",
        ):
            with self.assertRaisesRegex(ValueError, r"broken.*lint_rules"):
                repos.parse(manifest(good_entry(key="broken", lint_rules=bad)))
        with self.assertRaisesRegex(ValueError, "hub_lint_rules"):
            repos.parse({**manifest(good_entry()), "hub_lint_rules": [{"files": ["*"], "run": ""}]})

    def test_non_object_entry_names_index(self):
        with self.assertRaisesRegex(ValueError, r"repos\[0\]"):
            repos.parse(manifest("nope"))


class TestLoadOverride(unittest.TestCase):
    def test_env_override_and_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "m.json")
            path.write_text(json.dumps(manifest(good_entry(protected_branches=["trunk"]))), encoding="utf-8")
            with mock.patch.dict(os.environ, {repos.ENV_OVERRIDE: str(path)}):
                self.assertEqual(repos.load().protected_branches(), {"trunk"})
            self.assertEqual(repos.load(path).protected_branches(), {"trunk"})

    def test_invalid_json_is_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "m.json")
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                repos.load(path)


class TestCli(unittest.TestCase):
    def run_main(self, *argv):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = repos.main(list(argv))
        return code, out.getvalue()

    def test_list_prints_key_name_branch(self):
        code, out = self.run_main("--list")
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), len(repos.load().repos))
        self.assertIn("mobile uhis_lf_mobile develop", lines)

    def test_get_prints_fact(self):
        self.assertEqual(self.run_main("--get", "org"), (0, "Medtronic-LABS\n"))
        self.assertEqual(self.run_main("--get", "tracker"), (0, "leapwell\n"))
        self.assertEqual(self.run_main("--get", "project"), (0, "4\n"))


if __name__ == "__main__":
    unittest.main()
