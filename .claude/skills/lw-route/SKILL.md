---
name: lw-route
description: Route a LeapWell tracker issue into code-repo sub-issues - read Medtronic-LABS/leapwell#N, propose one sub-issue per affected repo from repos.json, privacy-scrub, preview, then create and link them as GitHub sub-issues only after an explicit yes.
argument-hint: <leapwell-issue-number>
disable-model-invocation: true
---

# Route leapwell #$ARGUMENTS

Tickets live in `Medtronic-LABS/leapwell` (the "what"); the work lives in code-repo sub-issues (the "how"). Process reference: `docs/process/SDLC.md`. Repo facts come only from `repos.json`.

1. **Read the item.** `gh issue view $ARGUMENTS -R Medtronic-LABS/leapwell --json number,title,body,labels,state,url,comments`
   If no number was given, ask for one. If it is closed, stop. List existing sub-issues: `gh api repos/Medtronic-LABS/leapwell/issues/$ARGUMENTS/sub_issues --jq '.[] | [.number, .repository_url, .state, .title] | @tsv'` - do not propose duplicates.

2. **Pick repos.** Read `repos.json` (keys, names, areas, stacks). Use any `area:<key>` label and the "Repo or component" section as hints, read the code if needed (`repos/<name>`), and propose the affected repos with a one-line reason each. Ask the developer to confirm or change the list.

3. **Draft one sub-issue per repo.**
   - Title: the parent's title with its prefix, narrowed to this repo's part (80 characters or fewer).
   - Body:
     ```markdown
     ## Summary
     <what this repo must do, 2-5 lines>

     ## Steps to reproduce / Acceptance criteria
     <copied from the parent: bug -> steps, expected, actual; feature/task -> acceptance criteria or What>

     Parent: Medtronic-LABS/leapwell#<N>
     ```
   - Label: the parent's `type:*` label (dropped if the repo lacks it).

4. **Privacy scrub.** For each draft, write `{"issue": {"title": "<title>", "body": "<body>", "labels": []}}` to a temp file with the Write tool and run `python3 scripts/sdlc/check_issue.py --scan-only --event <file>` (sub-issue drafts have no intake sections, so only the sensitive-data scan applies). It reports categories only; `"ok": false` means remove the flagged data (placeholders such as `<member-id>`) and re-run. Never paste patient data, names or tokens.
   If a draft targets `leapfrog-ai-service` (key `ai`), warn: that repo is private - people outside it will see the link from leapwell but not the sub-issue's details, so keep the shared context in the leapwell item.

5. **Preview** every sub-issue in full (repo, title, label, body) and ask: "Create these N sub-issues? (yes / change something)". Act only on an explicit yes; any edit -> re-scrub and preview again.

6. **Create and link**, per sub-issue:
   1. `gh issue create -R Medtronic-LABS/<name> --title '<title>' --body-file <tmpfile> --label <type:...>` (single-quote the title; on a missing-label error retry without `--label`). Note the new issue number `<n>` and URL.
   2. Database id (not the number): `gh api repos/Medtronic-LABS/<name>/issues/<n> --jq .id`
   3. Link: `gh api -X POST repos/Medtronic-LABS/leapwell/issues/$ARGUMENTS/sub_issues -F sub_issue_id=<id>`
   4. `gh project item-add 4 --owner Medtronic-LABS --url <issue-url>` (if this fails for a missing `project` scope, report it and continue).
   **Partial failure:** stop and report what was created so far. Never re-create an issue that exists. Give the exact command that retries only the failed step - e.g. the link failed: `gh api -X POST repos/Medtronic-LABS/leapwell/issues/$ARGUMENTS/sub_issues -F sub_issue_id=<id>` with the id already fetched; the project add failed: `gh project item-add 4 --owner Medtronic-LABS --url <issue-url>`. Run it only after the user's yes.

7. **Routing complete?** Ask: "Is routing complete for this item?" Only on yes:
   `gh issue edit $ARGUMENTS -R Medtronic-LABS/leapwell --add-label status:routed --remove-label status:triage`
   (`close-parents` closes the leapwell item once all its sub-issues are closed.) On no, leave the labels; more sub-issues can be added later with `/lw-route $ARGUMENTS`.

8. **Report** the sub-issue links and the next step for each: `/lw-start <repo-key> <n>`.

Never create, edit or label anything without an explicit yes; never set priority, assignees or project fields.
