"""Tests for scripts.sdlc.close_on_merge."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.sdlc import close_on_merge
from scripts.sdlc.close_on_merge import local_refs
from scripts.sdlc.close_parents import GhError


class TestLocalRefs(unittest.TestCase):
    def test_close_fix_resolve_variants(self):
        body = "Closes #12\nfixes #3\nResolved #7, Fixed #8 and closed #9"
        self.assertEqual(local_refs(body), [12, 3, 7, 8, 9])

    def test_refs_never_closes(self):
        self.assertEqual(local_refs("Refs #4\nref #5"), [])

    def test_cross_repo_excluded(self):
        self.assertEqual(local_refs("Closes Medtronic-LABS/leapwell#12\nFixes other/repo#3"), [])

    def test_mixed_and_deduplicated(self):
        self.assertEqual(local_refs("Closes #1\nCloses Medtronic-LABS/leapwell#2\nFixes #1\nRefs #3"), [1])

    def test_empty_and_none(self):
        self.assertEqual(local_refs(""), [])
        self.assertEqual(local_refs(None), [])

    def test_keyword_must_be_a_word(self):
        self.assertEqual(local_refs("prefixes #5 and disclosed #6"), [])


class TestMain(unittest.TestCase):
    def run_main(self, pull_request, *flags, gh=None):
        calls = []

        def fake_gh(args):
            calls.append(args)
            if gh:
                gh(args)
            return ""

        with tempfile.TemporaryDirectory() as tmp:
            event = Path(tmp) / "event.json"
            event.write_text(json.dumps({"pull_request": pull_request}))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = close_on_merge.main(
                    ["--event", str(event), "--repo", "Medtronic-LABS/uhis_lf_mobile", *flags], gh=fake_gh
                )
        return code, calls, out.getvalue()

    def pr(self, body, merged=True):
        return {"number": 77, "merged": merged, "body": body}

    def test_apply_closes_each_issue(self):
        code, calls, _ = self.run_main(self.pr("Closes #12\nFixes #3\nRefs #4"), "--apply")
        self.assertEqual(code, 0)
        self.assertEqual([c[:3] for c in calls], [["issue", "close", "12"], ["issue", "close", "3"]])
        for call in calls:
            self.assertIn("--repo", call)
            self.assertEqual(call[call.index("--repo") + 1], "Medtronic-LABS/uhis_lf_mobile")

    def test_dry_run_makes_no_gh_call(self):
        code, calls, out = self.run_main(self.pr("Closes #12"))
        self.assertEqual((code, calls), (0, []))
        self.assertIn("would close #12", out)

    def test_unmerged_pr_closes_nothing(self):
        code, calls, _ = self.run_main(self.pr("Closes #12", merged=False), "--apply")
        self.assertEqual((code, calls), (0, []))

    def test_no_refs_is_ok(self):
        code, calls, _ = self.run_main(self.pr("Refs #12"), "--apply")
        self.assertEqual((code, calls), (0, []))

    def test_failure_continues_and_exits_1(self):
        def fail_first(args):
            if args[2] == "12":
                raise GhError("boom")

        code, calls, out = self.run_main(self.pr("Closes #12\nCloses #13"), "--apply", gh=fail_first)
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 2)
        self.assertIn("could not close #12", out)


if __name__ == "__main__":
    unittest.main()
