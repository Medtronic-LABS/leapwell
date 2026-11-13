---
name: lw-feature
description: L-size LeapWell feature flow in a code repo - brainstorm, spec, plan, subagent task loop with review, final review, then lw-pr. For new modules, schema, sync, auth, AI, push or cross-repo contract work.
argument-hint: <repo-key> <issue-number>
disable-model-invocation: true
---

# L-size feature: $ARGUMENTS

Use when `/lw-start` sized the issue **L**. `$ARGUMENTS` is `<repo-key> <N>`; read the repo's `repos.json` entry (`name`, `integration_branch`, `verify`, `notes`). You are the orchestrating main session: you hold the decisions, dispatch the `lw-*` agents, and keep the human in the loop at each gate. Process reference: `docs/process/SDLC.md`.
Pre-condition: `repos/<name>` is on the `feat/<N>-<slug>` branch (run `/lw-start` first if not). If the work spans several repos, each repo has its own sub-issue and branch; agree the cross-repo contract in the spec first.

1. **Brainstorm** (superpowers:brainstorming if installed). Otherwise: restate the problem from the sub-issue and its leapwell parent, ask clarifying questions one at a time, and agree scope and non-goals.

2. **Design / spec.** Dispatch the `lw-architect` agent with the repo key, issue number and agreed scope. Write the result to `repos/<name>/docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md`.
   **Gate:** a human approves the spec. Do not continue without it.

3. **Plan** (superpowers:writing-plans if installed). Otherwise write `repos/<name>/docs/superpowers/plans/YYYY-MM-DD-<slug>.md`: small tasks, each with files, failing test first, the exact test command (from the repo's `verify`), and expected result. Commit spec + plan (`docs(<area>): spec and plan for #<N>`).

4. **Task loop** (superpowers:subagent-driven-development if installed). For each task, in order:
   a. Dispatch `lw-implementer` with the repo key and the task text only (one task, TDD, one commit).
   b. Dispatch `lw-reviewer` on that task's commits. Needs **Spec ✅** and **Approved**; otherwise send findings back to `lw-implementer` and re-review.
   c. For auth / db / sync / AI / push / logging / consent changes, also dispatch `lw-security`; Frappe schema or query work, `lw-frappe-db`; CI or Docker changes, `lw-devops`.
   d. Record the task status in the plan (a ledger table: task, commit, review verdicts).
   Dispatch `lw-qa` for regression / negative / permission / offline tests where the plan calls for them.

5. **Final review.** Dispatch `lw-reviewer` on the whole branch diff against `origin/<integration_branch>` (superpowers:requesting-code-review if installed). Run the repo's full `verify` commands (skip empty ones, honour `notes`). Fix and re-review until Spec ✅ / Approved.

6. **Finish** with `/lw-pr <key> <N>` (superpowers:finishing-a-development-branch if installed). L-size PRs need two human reviews.

Never merge, never push to the integration branch or `main`, never set priority, never skip hooks.
