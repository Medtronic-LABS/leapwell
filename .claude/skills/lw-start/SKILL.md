---
name: lw-start
description: Pick up a LeapWell code-repo issue (a sub-issue routed from leapwell) - check Definition of Ready, size it S/M/L, create the <type>/<issue#>-<slug> branch from the repo's integration branch inside repos/<name>, and post the plan on the issue.
argument-hint: <repo-key> <issue-number>
disable-model-invocation: true
---

# Start work: $ARGUMENTS

Process reference: `docs/process/SDLC.md` (sizes, Definition of Ready, branching). Repo facts come only from `repos.json`.

1. **Resolve the repo and issue.** `$ARGUMENTS` is `<repo-key> <N>`, N being the issue in that code repo (a sub-issue).
   - Only a number given: if the current directory is under `repos/<name>`, use that repo. Otherwise it is probably a leapwell item - list its sub-issues (`gh api repos/Medtronic-LABS/leapwell/issues/<N>/sub_issues --jq '.[] | [.number, .repository_url, .title] | @tsv'`) and ask which one to start, or suggest `/lw-route <N>` first if it has none.
   - Read the repo's entry in `repos.json`: `name`, `integration_branch`, `verify`, `notes`. Unknown key -> show the valid keys (`python3 -m scripts.sdlc.repos --list`) and stop. If `repos/<name>` is missing, suggest `/lw-setup --only <key>`.

2. **Read the issue and its parent.** `gh issue view <N> -R Medtronic-LABS/<name> --json number,title,labels,body,comments,assignees,state`. If it is closed, stop. Find the parent from the body line `Parent: Medtronic-LABS/leapwell#M` and read it: `gh issue view <M> -R Medtronic-LABS/leapwell --json number,title,labels,body`.

3. **Definition of Ready.** Report each as ok / missing:
   - Steps to reproduce (bug) or acceptance criteria (feature/task) present in the sub-issue or parent; parent has no `status:needs-info`.
   - Triaged: the parent has a `prio:*` label (set by a human - you never set it).
   - Not `status:blocked` / `status:needs-design`; open questions answered.
   If something is missing, say what and ask whether to continue anyway. Do not edit issues to make them look ready.

4. **Size** per `docs/process/SDLC.md`: S (small, no new behaviour), M (new behaviour inside one feature), L (new module, schema, sync, auth, AI, push, cross-repo contract). Read the code in `repos/<name>` first; give a one-line reason.

5. **Branch.** Prefix from the parent's type: `type:bug` -> `fix`, `type:feature` -> `feat`, `type:task` -> `chore` (or `refactor` / `docs` / `test` if more accurate); a P0 prod bug the team agreed to hotfix -> `hotfix` from `main`.
   Name `<prefix>/<N>-<short-kebab-slug>` (e.g. `fix/123-sync-stuck-90`), N = the repo-local issue.
   ```
   git -C repos/<name> fetch origin
   git -C repos/<name> switch -c <branch> origin/<integration_branch>
   ```
   (hotfix: `origin/main`). If the branch exists, switch to it. If the clone is dirty, stop and ask.

6. **Plan comment.** Draft: size + reason, approach (3-6 bullets), files likely touched, test plan using the repo's verify commands (skip empty ones; show `notes`), next step. No patient data, secrets or raw logs. Write it to a temp file with the Write tool; show it and post only after the user says yes: `gh issue comment <N> -R Medtronic-LABS/<name> --body-file <tmpfile>`.
   Offer to assign the issue to the user (`gh issue edit <N> -R Medtronic-LABS/<name> --add-assignee @me`). Moving Project cards is the user's call.

7. **Next.** S/M -> `/lw-fix <key> <N>`. L -> `/lw-feature <key> <N>`.

Never set priority, never push to the integration branch or `main`, never skip hooks.
