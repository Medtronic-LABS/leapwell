"""Tests for scripts.sdlc.close_parents."""
import contextlib
import io
import json
import unittest

from scripts.sdlc import close_parents
from scripts.sdlc.close_parents import GhError, decide

REPO = "Medtronic-LABS/leapwell"


AUTO = "auto"


def parent(state="open", labels=("status:routed",), number=1, total=AUTO):
    issue = {"number": number, "state": state, "labels": [{"name": n} for n in labels]}
    if total == AUTO:
        issue["_auto_total"] = True
    elif total is not None:
        issue["sub_issues_summary"] = {"total": total}
    return issue


def sub(state="closed", reason="completed", n=10):
    return {"number": n, "state": state, "state_reason": reason, "html_url": f"https://github.com/x/y/issues/{n}"}


class TestDecide(unittest.TestCase):
    def test_happy_path(self):
        self.assertTrue(decide(parent(), [sub(n=1), sub(n=2)]))

    def test_zero_subs_never_closes(self):
        self.assertFalse(decide(parent(), []))

    def test_any_open_sub_blocks(self):
        self.assertFalse(decide(parent(), [sub(), sub("open", None, 11)]))

    def test_missing_routed_label_blocks(self):
        self.assertFalse(decide(parent(labels=("bug",)), [sub()]))
        self.assertFalse(decide(parent(labels=()), [sub()]))

    def test_already_closed_parent_is_left_alone(self):
        self.assertFalse(decide(parent("closed"), [sub()]))

    def test_unreadable_sub_blocks(self):
        self.assertFalse(decide(parent(), [sub()], unreadable=1))

    def test_not_planned_counts_as_closed(self):
        self.assertTrue(decide(parent(), [sub(reason="not_planned"), sub(reason=None, n=11)]))


class FakeGh:
    def __init__(self, parents, subs_by_number, failing=()):
        self.parents = parents
        for issue in parents:
            if issue.pop("_auto_total", False):
                issue["sub_issues_summary"] = {"total": len(subs_by_number[issue["number"]])}
        self.subs_by_number = subs_by_number
        self.failing = set(failing)
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        path = args[-1] if "-f" not in args else args[args.index("-X") + 2]
        if "/sub_issues" in path:
            number = int(path.split("/issues/")[1].split("/")[0])
            if number in self.failing:
                raise GhError("boom")
            return json.dumps(self.subs_by_number[number])
        if "-X" in args:
            return "{}"
        return json.dumps(self.parents)

    def writes(self):
        return [c for c in self.calls if "-X" in c]


class TestProcess(unittest.TestCase):
    def setUp(self):
        stdout = contextlib.redirect_stdout(io.StringIO())
        stdout.__enter__()
        self.addCleanup(stdout.__exit__, None, None, None)

    def test_dry_run_default_makes_no_write_call(self):
        gh = FakeGh([parent(number=5)], {5: [sub()]})
        self.assertEqual(close_parents.main(["--repo", REPO], gh=gh), 0)
        self.assertEqual(gh.writes(), [])

    def test_apply_comments_with_sub_urls_then_closes(self):
        gh = FakeGh([parent(number=5)], {5: [sub(n=10), sub(n=11)]})
        self.assertEqual(close_parents.process(REPO, True, gh), [5])
        close, comment = gh.writes()
        self.assertIn("/issues/5/comments", comment[-3])
        self.assertIn("https://github.com/x/y/issues/10", comment[-1])
        self.assertIn("https://github.com/x/y/issues/11", comment[-1])
        self.assertIn("state=closed", close)

    def test_apply_skips_unsafe_parents(self):
        gh = FakeGh(
            [parent(number=1), parent(number=2), parent(number=3, labels=("bug",)), parent(number=4)],
            {1: [], 2: [sub(), sub("open", None, 11)], 3: [sub()], 4: [sub()]},
            failing={4},
        )
        self.assertEqual(close_parents.process(REPO, True, gh), [])
        self.assertEqual(gh.writes(), [])

    def test_unreadable_parent_does_not_stop_others(self):
        gh = FakeGh([parent(number=4), parent(number=5)], {4: [sub()], 5: [sub()]}, failing={4})
        self.assertEqual(close_parents.process(REPO, True, gh), [5])

    def test_pull_requests_ignored(self):
        pr = dict(parent(number=7), pull_request={})
        gh = FakeGh([pr], {7: [sub()]})
        self.assertEqual(close_parents.process(REPO, True, gh), [])

    def test_paginated_pages_are_flattened(self):
        text = json.dumps([parent(number=1)]) + json.dumps([parent(number=2)])
        self.assertEqual([p["number"] for p in close_parents._json_pages(text)], [1, 2])

    def test_hidden_sub_issues_block_close(self):
        gh = FakeGh([parent(number=5, total=3)], {5: [sub(n=10), sub(n=11)]})
        self.assertEqual(close_parents.process(REPO, True, gh), [])
        self.assertEqual(gh.writes(), [])

    def test_missing_summary_blocks_close(self):
        gh = FakeGh([parent(number=5, total=None)], {5: [sub()]})
        self.assertEqual(close_parents.process(REPO, True, gh), [])
        self.assertEqual(gh.writes(), [])

    def test_matching_summary_total_closes(self):
        gh = FakeGh([parent(number=5, total=2)], {5: [sub(n=10), sub(n=11)]})
        self.assertEqual(close_parents.process(REPO, True, gh), [5])

    def test_unreadable_count(self):
        self.assertEqual(close_parents.unreadable_count(parent(total=3), [sub(), sub()]), 1)
        self.assertEqual(close_parents.unreadable_count(parent(total=1), [sub()]), 0)
        self.assertEqual(close_parents.unreadable_count(parent(total=None), [sub()]), 1)
        self.assertEqual(close_parents.unreadable_count(parent(total=1), None), 1)

    def test_close_happens_before_comment(self):
        gh = FakeGh([parent(number=5)], {5: [sub()]})
        close_parents.process(REPO, True, gh)
        self.assertEqual(gh.writes()[0][2], "PATCH")
        self.assertEqual(gh.writes()[1][2], "POST")

    def test_failed_close_posts_no_comment(self):
        class FailingClose(FakeGh):
            def __call__(self, args):
                if "PATCH" in args:
                    self.calls.append(args)
                    raise GhError("nope")
                return super().__call__(args)

        gh = FailingClose([parent(number=5)], {5: [sub()]})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(close_parents.main(["--repo", REPO, "--apply"], gh=gh), 1)
        self.assertFalse([c for c in gh.calls if "POST" in c])

    def test_malformed_json_exits_1_without_traceback(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = close_parents.main(["--repo", REPO], gh=lambda args: "{not json")
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err.getvalue())

    def test_gh_failure_listing_returns_error_code(self):
        def failing(args):
            raise GhError("nope")

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(close_parents.main(["--repo", REPO], gh=failing), 1)


if __name__ == "__main__":
    unittest.main()
