"""Tests for scripts.sdlc.project_board."""

import contextlib
import io
import json
import unittest

from scripts.sdlc import project_board, repos
from scripts.sdlc.close_parents import GhError
from scripts.sdlc.project_board import Item, plan_sprints, sprint_mismatches

ORG = "Medtronic-LABS"
TRACKER = f"{ORG}/leapwell"
S1 = ("it-1", "Sprint 01")
S2 = ("it-2", "Sprint 02")


def item(content_id, *, parent=None, sprint=None, state="OPEN", issue_type=None, repo=TRACKER, number=1):
    return Item(
        item_id=f"item-{content_id}",
        content_id=content_id,
        repo=repo,
        number=number,
        state=state,
        issue_type=issue_type,
        parent_id=parent,
        sprint=sprint,
    )


class TestPlanSprints(unittest.TestCase):
    def test_child_takes_the_parent_sprint(self):
        changes = plan_sprints([item("story", sprint=S1), item("task", parent="story")])
        self.assertEqual([(c.item.content_id, c.sprint) for c in changes], [("task", S1)])

    def test_cascades_story_to_task_to_subtask(self):
        items = [item("subtask", parent="task"), item("task", parent="story"), item("story", sprint=S1)]
        changes = plan_sprints(items)
        self.assertEqual({c.item.content_id: c.sprint for c in changes}, {"task": S1, "subtask": S1})

    def test_never_overwrites_an_existing_sprint(self):
        self.assertEqual(plan_sprints([item("story", sprint=S1), item("task", parent="story", sprint=S2)]), [])

    def test_closed_children_are_left_alone(self):
        self.assertEqual(plan_sprints([item("story", sprint=S1), item("task", parent="story", state="CLOSED")]), [])

    def test_parent_without_sprint_or_outside_project_changes_nothing(self):
        self.assertEqual(plan_sprints([item("story"), item("task", parent="story")]), [])
        self.assertEqual(plan_sprints([item("task", parent="not-in-project")]), [])

    def test_mismatches_are_reported_not_changed(self):
        items = [item("story", sprint=S1), item("task", parent="story", sprint=S2, number=9)]
        self.assertEqual(plan_sprints(items), [])
        self.assertEqual([m.number for m in sprint_mismatches(items)], [9])


def page(nodes, sprint_field="field-sprint"):
    # Non-iteration fields come back as empty objects from the inline fragment.
    fields = [{}, {"id": "field-other", "name": "Cycle"}]
    if sprint_field:
        fields.append({"id": sprint_field, "name": "Sprint"})
    project = {"id": "proj-1", "fields": {"nodes": fields}, "items": {"nodes": nodes}}
    return json.dumps({"data": {"organization": {"projectV2": project}}})


def node(content_id, *, parent=None, sprint=None, state="OPEN", issue_type=None, repo=TRACKER, number=1):
    return {
        "id": f"item-{content_id}",
        "sprint": {"iterationId": sprint[0], "title": sprint[1]} if sprint else None,
        "content": {
            "__typename": "Issue",
            "id": content_id,
            "number": number,
            "state": state,
            "repository": {"nameWithOwner": repo},
            "issueType": {"name": issue_type} if issue_type else None,
            "parent": {"id": parent} if parent else None,
        },
    }


class FakeGh:
    def __init__(self, project_pages, issues=None, fail=()):
        self.project_pages = project_pages
        self.issues = issues or {}
        self.fail = fail
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        joined = " ".join(args)
        if any(marker in joined for marker in self.fail):
            raise GhError("gh api failed (exit 1)")
        if args[:2] == ["api", "graphql"] and "mutation" not in joined:
            return "".join(self.project_pages)
        for slug, issues in self.issues.items():
            if f"repos/{slug}/issues?" in joined:
                return json.dumps(issues)
        return "[]" if "/issues?" in joined else "{}"

    def mutations(self):
        return [c for c in self.calls if "mutation" in " ".join(c)]

    def writes(self):
        return [c for c in self.calls if c[0] == "project" or "PATCH" in c or "mutation" in " ".join(c)]


def run_main(argv, gh):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = project_board.main(argv, gh=gh)
    return code, out.getvalue(), err.getvalue()


class TestLoad(unittest.TestCase):
    def test_reads_every_page_and_skips_drafts_and_pull_requests(self):
        drafts = {"id": "item-d", "sprint": None, "content": None}
        pull = {"id": "item-p", "sprint": None, "content": {"__typename": "PullRequest"}}
        gh = FakeGh([page([node("a", sprint=S1), drafts]), page([pull, node("b", parent="a")])])
        board = project_board.load_board(ORG, 4, gh)
        self.assertEqual((board.project_id, board.sprint_field_id), ("proj-1", "field-sprint"))
        self.assertEqual([i.content_id for i in board.items], ["a", "b"])
        self.assertEqual(board.items[0].sprint, S1)


class TestSprintSync(unittest.TestCase):
    def setUp(self):
        self.pages = [page([node("story", sprint=S1, number=3), node("task", parent="story", number=35)])]

    def test_dry_run_lists_and_writes_nothing(self):
        gh = FakeGh(self.pages)
        code, out, _ = run_main(["sprint-sync"], gh)
        self.assertEqual((code, gh.writes()), (0, []))
        self.assertIn("leapwell#35: would set Sprint 01", out)
        self.assertIn("pass --apply", out)

    def test_apply_sets_the_iteration(self):
        gh = FakeGh(self.pages)
        code, out, _ = run_main(["sprint-sync", "--apply"], gh)
        self.assertEqual(code, 0)
        (mutation,) = gh.mutations()
        for expected in ("itemId=item-task", "fieldId=field-sprint", "iterationId=it-1", "projectId=proj-1"):
            self.assertIn(expected, mutation)
        self.assertIn("leapwell#35: set Sprint 01", out)

    def test_missing_sprint_field_is_a_clear_error(self):
        gh = FakeGh([page([node("story")], sprint_field=None)])
        code, _, err = run_main(["sprint-sync"], gh)
        self.assertEqual(code, 1)
        self.assertIn("no Sprint field", err)

    def test_a_failed_write_is_counted_and_the_run_continues(self):
        pages = [page([node("s", sprint=S1), node("t1", parent="s", number=1), node("t2", parent="s", number=2)])]
        gh = FakeGh(pages, fail=("itemId=item-t1",))
        code, out, err = run_main(["sprint-sync", "--apply"], gh)
        self.assertEqual(code, 1)
        self.assertIn("leapwell#2: set Sprint 01", out)
        self.assertIn("1 change(s) failed", err)


class TestReconcile(unittest.TestCase):
    def issue(self, number, node_id, labels=(), issue_type=None, **extra):
        return {
            "number": number,
            "node_id": node_id,
            "html_url": f"https://github.com/{TRACKER}/issues/{number}",
            "title": "t",
            "labels": [{"name": n} for n in labels],
            "type": {"name": issue_type} if issue_type else None,
            **extra,
        }

    def test_adds_only_missing_open_issues_and_skips_pull_requests(self):
        issues = {
            TRACKER: [
                self.issue(1, "in-project"),
                self.issue(2, "missing"),
                self.issue(5, "a-pr", pull_request={}),
            ]
        }
        gh = FakeGh([page([node("in-project")])], issues)
        code, out, _ = run_main(["reconcile", "--apply"], gh)
        self.assertEqual(code, 0)
        adds = [c for c in gh.calls if c[0] == "project"]
        self.assertEqual(
            adds, [["project", "item-add", "4", "--owner", ORG, "--url", f"https://github.com/{TRACKER}/issues/2"]]
        )
        self.assertIn("leapwell#2: added to the project", out)

    def test_lists_every_manifest_repo(self):
        gh = FakeGh([page([])])
        run_main(["reconcile"], gh)
        listed = " ".join(" ".join(c) for c in gh.calls)
        for repo in repos.load().repos:
            self.assertIn(f"repos/{ORG}/{repo.name}/issues?state=open", listed)
        self.assertIn(f"repos/{TRACKER}/issues?state=open", listed)

    def test_types_tracker_issues_from_their_label(self):
        issues = {TRACKER: [self.issue(1, "a", labels=("type:feature",)), self.issue(2, "b", ("type:bug",), "Bug")]}
        gh = FakeGh([page([node("a"), node("b")])], issues)
        code, out, _ = run_main(["reconcile", "--apply"], gh)
        patches = [c for c in gh.calls if "PATCH" in c]
        self.assertEqual(patches, [["api", "-X", "PATCH", f"repos/{TRACKER}/issues/1", "-f", "type=Story"]])
        self.assertEqual(code, 0)

    def test_types_untyped_children_from_their_parent(self):
        code_repo = f"{ORG}/spice-coaching"
        nodes = [
            node("task-ticket", issue_type="Task", number=3),
            node("child", parent="task-ticket", repo=code_repo, number=35),
            node("typed-child", parent="task-ticket", repo=code_repo, number=36, issue_type="Bug"),
            node("closed-child", parent="task-ticket", repo=code_repo, number=37, state="CLOSED"),
        ]
        gh = FakeGh([page(nodes)])
        run_main(["reconcile", "--apply"], gh)
        patches = [c for c in gh.calls if "PATCH" in c]
        self.assertEqual(patches, [["api", "-X", "PATCH", f"repos/{code_repo}/issues/35", "-f", "type=Subtask"]])

    def test_children_follow_a_type_set_in_the_same_run_and_untyped_parents_are_not_guessed(self):
        code_repo = f"{ORG}/spice-coaching"
        nodes = [
            node("ticket", number=3),
            node("child", parent="ticket", repo=code_repo, number=35),
            node("orphan-parent", number=8),
            node("orphan-child", parent="orphan-parent", repo=code_repo, number=40),
        ]
        issues = {TRACKER: [self.issue(3, "ticket", labels=("type:task",)), self.issue(8, "orphan-parent")]}
        gh = FakeGh([page(nodes)], issues)
        run_main(["reconcile", "--apply"], gh)
        patches = [(c[3], c[-1]) for c in gh.calls if "PATCH" in c]
        self.assertEqual(
            patches,
            [(f"repos/{TRACKER}/issues/3", "type=Task"), (f"repos/{code_repo}/issues/35", "type=Subtask")],
        )

    def test_dry_run_writes_nothing(self):
        issues = {TRACKER: [self.issue(2, "missing", labels=("type:task",))]}
        gh = FakeGh([page([])], issues)
        code, out, _ = run_main(["reconcile"], gh)
        self.assertEqual((code, gh.writes()), (0, []))
        self.assertIn("leapwell#2: would add to the project", out)
        self.assertIn("leapwell#2: would set type Task", out)

    def test_unreadable_repo_is_reported_and_the_run_continues(self):
        issues = {TRACKER: [self.issue(2, "missing")]}
        gh = FakeGh([page([])], issues, fail=(f"repos/{ORG}/leapfrog-ai-service/issues",))
        code, out, err = run_main(["reconcile", "--apply"], gh)
        self.assertEqual(code, 1)
        self.assertIn("leapwell#2: added to the project", out)
        self.assertIn("leapfrog-ai-service: could not list issues", err)


if __name__ == "__main__":
    unittest.main()
