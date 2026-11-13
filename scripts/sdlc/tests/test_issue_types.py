"""Tests for scripts.sdlc.issue_types."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.sdlc import issue_types
from scripts.sdlc.close_parents import GhError
from scripts.sdlc.patterns import ISSUE_TYPES, REQUIRED_SECTIONS

REPO = "Medtronic-LABS/leapwell"
CODE_REPO = "Medtronic-LABS/spice-coaching"


class FakeGh:
    """Records gh calls; answers issue reads from `issues` and can fail writes."""

    def __init__(self, issues=None, fail_writes=False):
        self.issues = issues or {}
        self.fail_writes = fail_writes
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if "PATCH" in args:
            if self.fail_writes:
                raise GhError("gh api failed (exit 1)")
            return "{}"
        return json.dumps(self.issues[args[-1]])

    @property
    def writes(self):
        return [call for call in self.calls if "PATCH" in call]


def run_main(argv, gh):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = issue_types.main(argv, gh=gh)
    return code, out.getvalue(), err.getvalue()


def event_file(directory, issue):
    path = Path(directory) / "event.json"
    path.write_text(json.dumps({"issue": issue, "repository": {"full_name": REPO}}), encoding="utf-8")
    return str(path)


class TestMapping(unittest.TestCase):
    def test_every_intake_kind_has_a_native_type(self):
        self.assertEqual(set(ISSUE_TYPES), set(REQUIRED_SECTIONS))
        self.assertEqual(ISSUE_TYPES["feature"], "Story")
        self.assertEqual(ISSUE_TYPES["epic"], "Epic")
        self.assertEqual(ISSUE_TYPES["release"], "Task")

    def test_native_type_from_label_or_title(self):
        self.assertEqual(issue_types.native_type("anything", ["type:feature"]), "Story")
        self.assertEqual(issue_types.native_type("[Bug] crash", []), "Bug")
        self.assertIsNone(issue_types.native_type("no prefix", ["area:mobile"]))

    def test_child_type_follows_the_parent(self):
        for parent in ("Story", "Bug", "Epic", "Feature", None):
            self.assertEqual(issue_types.child_type(parent), "Task", parent)
        for parent in ("Task", "Subtask"):
            self.assertEqual(issue_types.child_type(parent), "Subtask", parent)

    def test_parse_ref(self):
        self.assertEqual(issue_types.parse_ref("Medtronic-LABS/leapwell#3"), (REPO, 3))
        for bad in ("leapwell#3", "Medtronic-LABS/leapwell", "Medtronic-LABS/leapwell#x", "#3"):
            with self.assertRaises(ValueError, msg=bad):
                issue_types.parse_ref(bad)


class TestEventMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def issue(self, **extra):
        return {"number": 7, "title": "[Feature] x", "labels": [{"name": "type:feature"}], **extra}

    def test_sets_type_from_label_when_untyped(self):
        gh = FakeGh()
        code, out, _ = run_main(["--event", event_file(self.tmp.name, self.issue()), "--apply"], gh)
        self.assertEqual(code, 0)
        self.assertEqual(gh.writes, [["api", "-X", "PATCH", f"repos/{REPO}/issues/7", "-f", "type=Story"]])
        self.assertIn("#7: type set to Story", out)

    def test_dry_run_makes_no_call(self):
        gh = FakeGh()
        code, out, _ = run_main(["--event", event_file(self.tmp.name, self.issue())], gh)
        self.assertEqual((code, gh.calls), (0, []))
        self.assertIn("would set type Story", out)

    def test_never_overrides_a_type_someone_chose(self):
        gh = FakeGh()
        event = event_file(self.tmp.name, self.issue(type={"name": "Epic"}))
        code, out, _ = run_main(["--event", event, "--apply"], gh)
        self.assertEqual((code, gh.calls), (0, []))
        self.assertIn("already Epic", out)

    def test_unknown_kind_is_left_alone(self):
        gh = FakeGh()
        event = event_file(self.tmp.name, {"number": 7, "title": "hello", "labels": []})
        code, out, _ = run_main(["--event", event, "--apply"], gh)
        self.assertEqual((code, gh.calls), (0, []))
        self.assertIn("no type label", out)

    def test_failed_write_is_reported_without_response_content(self):
        gh = FakeGh(fail_writes=True)
        code, _, err = run_main(["--event", event_file(self.tmp.name, self.issue()), "--apply"], gh)
        self.assertEqual(code, 1)
        self.assertIn("issue-types failed", err)


class TestChildMode(unittest.TestCase):
    def gh(self, parent_type, child_type=None):
        return FakeGh(
            {
                f"repos/{REPO}/issues/3": {"number": 3, "type": {"name": parent_type} if parent_type else None},
                f"repos/{CODE_REPO}/issues/35": {"number": 35, "type": {"name": child_type} if child_type else None},
            }
        )

    def argv(self, *extra):
        return ["--issue", f"{CODE_REPO}#35", "--parent", f"{REPO}#3", *extra]

    def test_child_of_a_task_becomes_subtask(self):
        gh = self.gh("Task")
        code, out, _ = run_main(self.argv("--apply"), gh)
        self.assertEqual(code, 0)
        self.assertEqual(gh.writes, [["api", "-X", "PATCH", f"repos/{CODE_REPO}/issues/35", "-f", "type=Subtask"]])
        self.assertIn("#35: type set to Subtask", out)

    def test_child_of_a_story_becomes_task(self):
        gh = self.gh("Story")
        run_main(self.argv("--apply"), gh)
        self.assertEqual(gh.writes[0][-1], "type=Task")

    def test_typed_child_is_left_alone(self):
        gh = self.gh("Story", child_type="Bug")
        code, out, _ = run_main(self.argv("--apply"), gh)
        self.assertEqual((code, gh.writes), (0, []))
        self.assertIn("already Bug", out)

    def test_issue_requires_parent(self):
        with self.assertRaises(SystemExit):
            run_main(["--issue", f"{CODE_REPO}#35"], FakeGh())

    def test_bad_ref_exits_one(self):
        code, _, err = run_main(["--issue", "nope", "--parent", f"{REPO}#3"], FakeGh())
        self.assertEqual(code, 1)
        self.assertIn("issue-types failed", err)


if __name__ == "__main__":
    unittest.main()
