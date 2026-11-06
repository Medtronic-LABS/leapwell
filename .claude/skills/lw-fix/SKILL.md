---
name: lw-fix
description: S/M-size LeapWell fix flow in a code repo - systematic debugging, failing test, minimal fix, the repo's verify commands, reviewer agent, then lw-pr. For bugs and small changes inside one feature.
argument-hint: <repo-key> <issue-number>
disable-model-invocation: true
---

# S/M fix: $ARGUMENTS

Use when `/lw-start` sized the issue **S** or **M**. `$ARGUMENTS` is `<repo-key> <N>` (or just `<N>` when the repo is clear from `repos/<name>` or the current branch). Read the repo's `repos.json` entry (`name`, `integration_branch`, `verify`, `notes`). Pre-condition: `repos/<name>` is on the `<type>/<N>-<slug>` branch. Process reference: `docs/process/SDLC.md`.

1. **Understand** (superpowers:systematic-debugging if installed). Otherwise: read the issue's steps (and its leapwell parent), reproduce (test, emulator, local stack, or by reading the code path), find the root cause - not just the symptom - and state it in one sentence with `path:line`. No fix before a root cause.

2. **M-size only:** write a short design note (approach, files, offline behaviour, risks) and show it to the user before coding; it goes into the PR description later.

3. **Failing test** (superpowers:test-driven-development if installed). Write a test that fails because of the bug (or proves the new behaviour). Run it; confirm it fails for the right reason. `lw-qa` can write it if the user prefers.

4. **Fix.** Minimal change that makes the test pass, following leapwell `CLAUDE.md` "Engineering Design Standards" and `repos/<name>/CLAUDE.md`. Run the focused tests, then the repo's `verify.lint` and `verify.test` from `repos.json` (run them inside `repos/<name>`; skip empty commands and tell the user `notes`, e.g. Frappe repos need the `env/frappe` bench). Stay within any failure budget the repo's own CI workflow defines.

5. **Commit.** `git -C repos/<name> commit` with `fix(<area>): <summary> (#<N>)` - hooks run; never `--no-verify`.

6. **Review.** Dispatch the `lw-reviewer` agent on `git -C repos/<name> diff origin/<integration_branch>...HEAD` with the repo key and issue number. Needs **Spec ✅** and **Approved**; fix and re-review otherwise. For auth / db / sync / AI / logging / consent changes also dispatch `lw-security`; for slow queries or Frappe patches, `lw-frappe-db`.

7. **PR.** `/lw-pr <key> <N>`.

Never merge, never push to the integration branch or `main`, never set priority.
