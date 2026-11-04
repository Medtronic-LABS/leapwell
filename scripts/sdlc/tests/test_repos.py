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
    "mobile": "develop", "core": "main", "shukhee": "main", "ai": "develop",
    "coaching": "leapwell-main", "coaching-android": "leapwell-main", "coaching-dashboard": "leapwell-main",
}


def good_entry(**over):
    entry = {
        "key": "k", "name": "n", "area": "a", "stack": "s", "integration_branch": "main",
        "protected_branches": ["main"], "verify": {"test": "t", "lint": "l", "build": "b"},
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


if __name__ == "__main__":
    unittest.main()
