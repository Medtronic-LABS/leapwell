# The LeapWell board: hierarchy, sprints and views

How the org Project "LeapWell" (#4) is used for Scrum. The lifecycle, statuses, sizes and gates are in
[SDLC.md](SDLC.md) and are not repeated here; setting the board up is in [ADMIN_SETUP.md](ADMIN_SETUP.md).

## Hierarchy

Five native issue types. GitHub links them with sub-issues; one issue has one parent.

| Level | Issue type | Lives in | Created by | Parent |
|---|---|---|---|---|
| 1 | Epic | `leapwell` | Epic form or `/lw-ticket` | none |
| 2 | Story | `leapwell` | **Feature request** form, `/lw-ticket`, `/lw-promote` | an Epic (optional) |
| 2 | Bug | `leapwell` | Bug form or `/lw-ticket` | a Story or none |
| 3 | Task | the code repo, or `leapwell` for a task ticket | `/lw-route` (sub-issue of a Story or Bug); Task form | a Story or Bug |
| 4 | Subtask | the code repo | `/lw-route` under a task ticket, or "Create sub-issue" on a Task | a Task |

- Reporters still file a "Feature request" with the `type:feature` label; its issue type is Story.
- The type is set automatically: the `issue-check` workflow sets it from the `type:*` label on every new
  leapwell issue, and `/lw-route` sets Task or Subtask on the sub-issues it creates. The mapping has one
  home, `ISSUE_TYPES` in `scripts/sdlc/patterns.py`.
- A release ticket is a Task with the `type:release` label. The org's `Feature` type is not used here.
- GitHub enforces none of this. Check the hygiene filters below at every sprint planning.

## Fields

| Field | Used for |
|---|---|
| Status | The lifecycle in SDLC.md section 4 |
| Sprint | Two-week iterations, Monday to Sunday, named `Sprint 01`, `Sprint 02`, ... |
| Story Points | Estimate on a Story, a Bug, or a Task that has no parent. Sub-issues carry no points |
| Priority | Board ordering. The `prio:*` label stays the record a human sets at triage |
| Start date / Target date | Epics on the roadmap |
| Size | The S / M / L process path from SDLC.md section 3 (not an estimate) |

Sprint 01 starts on Monday 2026-11-16. Whoever runs sprint planning adds six more sprints in the field's
settings whenever fewer than three future sprints remain; GitHub does not create them on its own.

## Views

| View | Shows | Use it for |
|---|---|---|
| Product Backlog | Every open item, as a hierarchy, by priority | Grooming and ordering |
| Sprint Planning | Open items except Epics, grouped by Sprint, with Story Points totals | Sprint planning |
| Active Sprint | The current sprint as a board by Status | Standup, review, QA |
| Release Roadmap | Epics from Start date to Target date | Release planning |
| My Work | Open items assigned to you, by Status | Your day |

## Sprint planning checklist

1. Run `python3 -m scripts.sdlc.project_board reconcile` and read the list. With `--apply` it adds open
   issues that are missing from the board and sets missing issue types.
2. In **Sprint Planning**, clear the hygiene filters:
   - `no:type` - untyped items; give each a type.
   - `type:Story no:parent-issue` - Stories outside any Epic; fine if deliberate.
   - `type:Subtask no:parent-issue` - a Subtask must have a parent Task.
3. Give each candidate Story and Bug its Story Points, then drag the committed ones from "No Sprint" into
   the sprint. The Story Points total of the group is the commitment.
4. Run `python3 -m scripts.sdlc.project_board sprint-sync`, then again with `--apply`. GitHub does not copy
   a Story's sprint to its Tasks and Subtasks; this fills the gaps. It never overwrites a Sprint.
5. A sub-issue created mid-sprint gets its Sprint from the person who creates it, or from the next
   `sprint-sync` run.

Unfinished work is moved to the next sprint by hand at the sprint review; `sprint-sync` then lists any
sub-issue whose Sprint no longer matches its parent's.

## Reporting, and what GitHub does not give us

Insights charts (set up once, see ADMIN_SETUP.md): Story Points by Sprint and Status, items by Status for
the current sprint, items by assignee for the current sprint.

- No burndown and no burn-up: historical charts need a paid GitHub plan.
- No committed-versus-delivered velocity: sprint scope is not recorded at the start. Read the Sprint
  Planning totals at planning and at review.
- Developer workload is a count of items, not points, because points sit on the Story.
- Epic progress is the "Sub-issues progress" column: it counts issues, not points.
