---
name: lw-pr
description: Open a LeapWell draft pull request in a code repo - run the repo's verify commands from repos.json, fill the PR template with Closes #N (and Refs to the leapwell parent), push the feature branch and create a draft PR to the repo's integration branch only after an explicit yes.
argument-hint: "<repo-key> [issue-number]"
disable-model-invocation: true
---

# Open a draft PR: $ARGUMENTS

1. **Repo, branch and issue.** Resolve the repo from `$ARGUMENTS` (or the current `repos/<name>` directory) and read its `repos.json` entry (`name`, `integration_branch`, `verify`, `notes`). `git -C repos/<name> branch --show-current` must match `<type>/<N>-<slug>` - take N from it (or from `$ARGUMENTS`). Refuse on the integration branch or `main`.
   Base: `integration_branch`; `hotfix/*` -> `main` (remind the user to back-merge `main` into the integration branch after release).
   Parent: from the sub-issue body line `Parent: Medtronic-LABS/leapwell#M` (`gh issue view <N> -R Medtronic-LABS/<name> --json body`).

2. **Checks** inside `repos/<name>` (report each with the result; do not hide failures):
   - The repo's `verify.lint` and `verify.test` (focused tests for S; the full suite for M/L) and `verify.build` for M/L. Skip empty commands and show `notes` (Frappe repos run in the `env/frappe` bench). Stay within any failure budget the repo's own CI workflow defines.
   - `git -C repos/<name> status --porcelain` clean; `git -C repos/<name> log origin/<base>..HEAD --oneline` shows only this issue's commits.

3. **Body.** Fill `repos/<name>/.github/pull_request_template.md` (leapwell's `.github/pull_request_template.md` if the repo has none) into a temp file with the Write tool:
   - First line `Closes #<N>` (or `Refs #<N>` if it does not fully resolve the issue); then `Refs Medtronic-LABS/leapwell#<M>` when the parent is known. A small chore with no sub-issue may use `Refs Medtronic-LABS/leapwell#<M>` alone.
   - Summary (what and why, 2-5 lines; M-size: include the design note), size, test evidence (commands + results from step 2), screenshots (test data only), risk & rollback, checklist ticked honestly - leave unticked what is not done.
   - No patient data, secrets, tokens or raw logs.
   Show the title and full body, and ask "Push the branch and open this draft PR? (yes / change something)".

4. **Push and create** (only after yes):
   ```
   git -C repos/<name> push -u origin <branch>
   gh pr create --draft -R Medtronic-LABS/<name> --base <base> --head <branch> --title "<type>(<area>): <summary> (#<N>)" --body-file <tmpfile>
   ```
   Report the PR link. Because most integration branches are not the default branch, `lw-close-on-merge` closes `#<N>` when the PR merges. Marking it ready, requesting reviewers and merging are the human's steps.

Never merge, never push to the integration branch or `main`, never force-push, never skip hooks.
