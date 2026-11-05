---
name: lw-setup
description: Set up or refresh the LeapWell developer workspace - clone or fetch the seven code repos from repos.json into repos/, point their git hooks at leapwell's .githooks, and run the tool doctor. Safe to re-run.
argument-hint: "[--only key,key] [--ssh] [--no-clone] [--strict]"
disable-model-invocation: true
allowed-tools: Bash(bash scripts/workspace/setup.sh*), Bash(python3 -m scripts.workspace.doctor*), Bash(python3 -m scripts.sdlc.repos*), Bash(gh auth status*), Read
---

# LeapWell workspace setup

Run from the **leapwell root** (where `repos.json` is). Claude is always started from here; the code repos live in `repos/<name>`.

1. **Check the place.** `repos.json` and `scripts/workspace/setup.sh` must exist in the current directory. If not, tell the user to `cd` to their leapwell clone and start Claude there.

2. **Run setup.** `bash scripts/workspace/setup.sh $ARGUMENTS`
   Run each command in this skill as its own Bash call, exactly as written (no `&&`, `;` or `echo`): the skill's
   allowed tools cover single commands only, so a chained command stops at a permission prompt.
   Options: `--only mobile,core` limits to those repo keys; `--ssh` clones over SSH; `--no-clone` only re-wires hooks on existing clones; `--strict` exits non-zero on any problem.
   The script never resets, pulls, rebases or switches branches in an existing clone - it only fetches. New clones start on the repo's integration branch.

3. **Explain the per-repo lines.** For each `== <key> (<name>)` block say: cloned / fetched, current branch, and whether it is `DIRTY (left untouched)`. A failed clone or fetch usually means no access (e.g. `leapfrog-ai-service` is private - ask the team lead for access) or no network.

4. **Explain the doctor table** (`== tools`). Columns: tool, status, why it is needed.
   - `ok` - installed and working.
   - `MISSING` - not on `PATH`; it is needed only for the areas listed ("needed by Mobile app" means only mobile work needs it). Suggest the usual installer for the user's OS, without running it.
   - `FAIL` - present but unusable: `gh` not authenticated -> `gh auth login`; `python3` older than the minimum -> install a newer Python.
   Re-check a single area with `python3 -m scripts.workspace.doctor --only <key>`.

5. **Next steps.** List the repo keys and integration branches (`python3 -m scripts.sdlc.repos --list`) and point to:
   - `/lw-ticket` to file, `/lw-route <leapwell#>` to split a ticket into repo sub-issues,
   - `/lw-start <repo-key> <issue#>` to begin work on a sub-issue,
   - the area skills (`/lw-mobile-start`, `/lw-frappe-setup`, `/lw-ai-start`, `/lw-coaching-start`) for local stacks.

Never install software, change global git config, or touch a dirty clone without the user's explicit yes.
