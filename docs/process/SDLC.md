# LeapWell SDLC

How work moves from an idea to a release across the seven LeapWell code repos. Short on purpose:
ceremony scales with the size of the change. This file is the single home of the process; skills,
agents, CI and the other docs point here instead of repeating it.
Design record: [`docs/superpowers/specs/2026-11-04-leapwell-hub-design.md`](../superpowers/specs/2026-11-04-leapwell-hub-design.md).

- **Tracker:** GitHub Issues in `Medtronic-LABS/leapwell` plus org Project "LeapWell" (#4). The old Jira
  project (LEAP) is retired; the 412 existing `uhis_lf_mobile` issues stay where they are.
- **Repo facts** (names, integration branches, verify commands): [REPOS.md](REPOS.md), generated from `repos.json`.
- **The repo and the code repos are public** (except `leapfrog-ai-service`, which is private but treated the
  same way). No patient/member data, names, phone numbers, IDs, credentials, tokens, env values or
  unscrubbed logs in issues, PRs, commits, tests, mockups, wiki pages or screenshots. Security problems go to a
  [private advisory](https://github.com/Medtronic-LABS/leapwell/security/advisories/new).
- **Code standards:** the "Engineering Design Standards" section of `CLAUDE.md`.

```
 idea ──► Discussion (Ideas / Field feedback / Partner requests)
            │  PM: /lw-promote <discussion#>
 bug / task / release ─── /lw-ticket ───┐
            ▼                            ▼
        leapwell issue  ("what")                              Project Status
            │  triage (humans: priority, size, owner)          Triage → Backlog → Ready
            ▼  developer: /lw-route <N>
        code-repo sub-issues ("how"), one per affected repo
            │  /lw-start <repo> <n>   (Definition of Ready, size, branch)      In progress
            ▼  S/M: /lw-fix      L: /lw-feature (spec → plan → task loop)
        <type>/<n>-<slug> from the repo's integration branch
            │  /lw-pr  (checks, Closes #n, draft PR)
            ▼  CI + human review + human merge                                  In review
        lw-close-on-merge closes the sub-issue                                  QA
            ▼  close-parents closes the leapwell item when all sub-issues close Done
        /lw-release per repo (human tags and publishes)
```

## 1. Roles and human-only gates

| Role | Does |
|---|---|
| Reporter (anyone: dev, QA, PM) | Files tickets through Claude (`lw-ticket`) or the issue forms; posts ideas in Discussions |
| PM | Promotes agreed ideas (`lw-promote`), keeps the Wiki and mockups current |
| Triager (lead + PM, twice a week) | Sets priority, size, owner; moves Triage → Backlog/Ready |
| Developer | Routes items to repos (`lw-route`), picks up Ready sub-issues, works with the agents, owns the PR |
| Reviewer (human) | Reviews and approves PRs; CODEOWNERS for sensitive paths |
| QA | Verifies on the training build (mobile) or the target environment, moves the card to Done or back |
| Release owner | Bumps version, tags, publishes |

**Only humans may:** approve a spec, set priority, merge a PR, tag or release, upload to a store, change
GitHub settings (labels, branch protection, Project fields, Discussion categories, Wiki), handle prod keys /
secrets / `key.properties` / `env*.json`, and grant a security exception. Claude proposes; a person decides.

## 2. Ticket model

Two levels.

| Level | Where | Who files | Purpose |
|---|---|---|---|
| leapwell item | `Medtronic-LABS/leapwell` | anyone, via `lw-ticket` or `lw-promote` | The "what": feature, bug, task or release, with the required sections of its type |
| Sub-issue | the affected code repo | a developer, via `lw-route` | The "how": repro or acceptance criteria, back-link `Parent: Medtronic-LABS/leapwell#N` |

- Reporters never need to know which repo a bug belongs to; the bug form's "Repo or component (if known)" can
  be blank, and a developer routes it.
- `lw-route` creates one sub-issue per affected repo and links it as a GitHub sub-issue of the leapwell item.
  It adds `status:routed` only after the developer confirms routing is complete; sub-issues can still be added later.
- Items never routed (docs, releases, chores done inside leapwell) are closed by hand or by a leapwell PR.
- Issues stay enabled in code repos (sub-issues need them). Their issue chooser points people to leapwell.

## 3. Sizes

`/lw-start` proposes a size with a one-line reason; the developer can override it.

| Size | What it is | Required path |
|---|---|---|
| S | About 50 changed lines or fewer and no new behaviour: bug fix, copy, small refactor | sub-issue → branch → failing test + fix (`/lw-fix`) → `lw-reviewer` → PR → 1 human review |
| M | New behaviour inside one existing feature | as S, plus a short design note (approach, files, offline behaviour, risks) shown before coding and copied into the PR → 1 human review |
| L | New module, DB schema/migration, sync, auth, AI or push change, or a contract between repos — judged by nature, not line count | spec + plan under `docs/superpowers/` in the repo that owns the change (cross-repo L: in leapwell), human approves the spec, subagent task loop (`/lw-feature`), final whole-branch review → 2 human reviews |

Anything touching auth, db, sync, scribe/AI, push, logging, consent or build config also gets `lw-security`.

## 4. Issue lifecycle

Project #4 Status: Triage → Backlog → Ready → In progress → In review → QA → Done

| Status | Who moves it | Meaning |
|---|---|---|
| Triage | automatic (issue added) | New; not yet looked at |
| Backlog | triager | Accepted, prioritised, not scheduled |
| Ready | triager / lead | Meets the Definition of Ready; can be picked up |
| In progress | developer | Branch exists, work started |
| In review | developer | PR open and marked ready for review |
| QA | developer after merge | On the integration branch; waiting for QA |
| Done | QA (or automatic on close) | Verified; issue closed |

The Project's built-in Repository field separates leapwell items from code-repo sub-issues. The
`issue-check` workflow validates every leapwell issue against its form: missing sections or detected sensitive
data add `status:needs-info` and one bot comment; fixing the issue removes the label.

### Definition of Ready

- All required sections for its type are filled (no `status:needs-info`): a bug has steps to reproduce,
  expected and actual behaviour; a feature has acceptance criteria and offline behaviour.
- Triaged: a `prio:*` label (set by a human) on the leapwell item and an `area:*` label.
- Not `status:blocked` or `status:needs-design`; open questions answered.
- Size agreed; L-size has an approved spec before implementation starts.

### Definition of Done

- PR merged to the repo's integration branch with `Closes #n`; all required checks green.
- New public behaviour has a test; bugs have a regression test.
- Engineering Design Standards met: no hardcoded user-facing strings or config, no swallowed errors, no duplication.
- No secrets, env files or patient data committed.
- Offline behaviour verified where relevant.
- Docs, Wiki or mockups updated where behaviour or requirements changed.
- QA verified (mobile bugs: on the reported device and Android version when possible).

## 5. Branching

- Each repo's integration branch is in [REPOS.md](REPOS.md) (`develop`, `main` or `leapwell-main`). Nobody pushes
  to it or to `main` directly; the guard hook blocks it in Claude Code and branch protection on GitHub.
- Work branches from the integration branch: `<type>/<issue#>-<slug>`, `<issue#>` the repo-local sub-issue
  number, type one of `feat | fix | chore | docs | refactor | test | hotfix`. Example: `fix/123-sync-stuck-90`.
- Commits: Conventional Commit subject with the issue, e.g. `fix(sync): retry upload on 503 (#123)`. The
  `commit-msg` hook requires a `#N` or a Conventional Commit type.
- Keep a branch to one sub-issue. Never force-push shared branches.

## 6. Pull requests

- Open with `/lw-pr` (draft PR to the integration branch; `hotfix/*` to `main`). It runs the repo's verify
  commands from `repos.json` and fills the PR template.
- The body's first line is `Closes #n` (the repo-local sub-issue) or `Refs #n` when it does not fully resolve it,
  then `Refs Medtronic-LABS/leapwell#N` for the parent. A small chore without a sub-issue may use
  `Closes|Refs Medtronic-LABS/leapwell#N` alone. `pr-check` fails without an issue link; a bare `#N` in prose is not enough.
- Because most repos' integration branch is not the default branch, GitHub ignores `Closes` on merges there.
  The `lw-close-on-merge` workflow in each code repo closes the named local issues when the PR merges.
- Fill Summary, Test evidence, Risk & rollback; screenshots show test data only; tick the checklist honestly.
- Approvals: integration branch 1, `main` 2, plus CODEOWNERS for sensitive paths. L-size PRs need 2 human reviews.
- Stale approvals are dismissed on new pushes; conversations must be resolved before merge. A human merges.

## 7. CI gates

| Where | Workflow / job | Gate |
|---|---|---|
| leapwell | `ci.yml` / `sdlc-scripts` | `python3 -m unittest discover -s scripts -t .` must pass |
| leapwell | `ci.yml` / `secret-scan` | gitleaks (`--redact`) on the PR's commit range must be clean |
| leapwell | `ci.yml` / `mockup-scan` | `scripts/sdlc/scan_text.py mockups wiki` finds no patient data or secrets |
| leapwell | `pr-check.yml` | issue link present; branch name and sensitive-data checks |
| leapwell | `issue-check.yml` | issue sections and privacy (labels the issue; not a PR gate) |
| leapwell | `close-parents.yml` | hourly: closes routed items whose sub-issues are all closed |
| each code repo | `lw-pr-check`, `lw-secret-scan`, `lw-close-on-merge` | the thin layer from `templates/repo-layer/`; contains no logic, runs leapwell's scripts at a pinned ref |
| each code repo | its own build/test CI | stays in the repo; leapwell does not own it |

Required checks on leapwell `main`: `pr-check`, `sdlc-scripts`, `secret-scan`, `mockup-scan`.

Mobile has ratchet budgets (`ANALYZE_ERROR_BUDGET`, `TEST_FAILURE_BUDGET`) in the `flutter` job's `env:` of its
own `.github/workflows/ci.yml`; that file is the single source of the numbers. Ratchet down, never up: lower a
budget in the same PR that fixes errors; raising one needs an explicit human decision recorded in the PR.

### Keeping the code repos in line

`python3 scripts/sync/sync_repos.py --repo <key>` (or `--all`) renders the thin layer into `repos/<name>` and
prints a diff. `--apply` commits it on the local branch `chore/leapwell-sync`; it never pushes or opens PRs. Bumping
the pinned leapwell ref (`--ref`) is the way to roll out a script change. It is described in
[ADMIN_SETUP.md](ADMIN_SETUP.md).

## 8. Release

Per repo, when its owner decides. Walk the checklist with `/lw-release <repo-key>` (the `lw-release` agent checks readiness).

1. File a `[Release] <repo> <version>` item (`/lw-ticket` → Release).
2. Version bump in its own PR (`chore/<n>-bump-<version>`) to the integration branch. Mobile: `pubspec.yaml` is the
   only version source and the build number always increases; the full checklist is `RELEASE_PLAN.md` in `repos/uhis_lf_mobile`.
3. Integration branch → `main` PR once QA has verified the build (where the repo has both).
4. Release notes in user-facing language, no internal IDs or patient data; mobile also in English and Bangla, 500 characters or fewer each.
5. Tag and publish are human steps (mobile: `/lw-mobile-release dev|training|playstore` builds the artifact only;
   the Play Console rollout internal → closed → staged production is manual).
6. Tick the release item and close it.

## 9. Hotfix

For a production P0/P1 the team agrees cannot wait for the next release:

1. Sub-issue as usual; branch `hotfix/<n>-<slug>` from `origin/main`.
2. `/lw-fix` (failing test first); `/lw-pr` opens the PR to `main` (2 approvals).
3. Bump the version, tag and release as in section 8.
4. Back-merge `main` into the integration branch with a PR the same day.

## 10. Working with the agents

Everything Claude lives in this repo once (`.claude/`); start Claude from the leapwell root so every repo gets the same behaviour.

Process skills you run:

| Skill | When |
|---|---|
| `/lw-setup` | Clone or refresh the seven repos under `repos/`, wire hooks, check tools |
| `/lw-ticket` | File a bug, feature, task or release (also works in Claude chat with the org skill) |
| `/lw-promote <discussion#>` | PM: turn an agreed Discussion into a leapwell feature item |
| `/lw-route <N>` | Developer: create code-repo sub-issues for a leapwell item |
| `/lw-start <repo> <n>` | Pick up a sub-issue: Definition of Ready, size, branch, plan comment |
| `/lw-fix <repo> <n>` | S/M: root cause, failing test, fix, review |
| `/lw-feature <repo> <n>` | L: brainstorm, spec, plan, task loop, final review |
| `/lw-pr <repo>` | Run checks, fill the template, push the branch, open a draft PR |
| `/lw-release <repo>` | Release checklist and notes |
| `/lw-wiki <page>` | Edit the live GitHub Wiki (shows the diff, pushes on "yes") |

Run skills (all take no decisions for you; each states what it will run): `lw-mobile-start`, `lw-mobile-fresh-launch`,
`lw-mobile-e2e`, `lw-mobile-release`, `lw-frappe-setup`, `lw-frappe-start`, `lw-frappe-stop`, `lw-frappe-status`,
`lw-ai-start`, `lw-ai-stop`, `lw-ai-status`, `lw-ai-test`, `lw-coaching-start`, `lw-coaching-stop`,
`lw-coaching-status`, `lw-coaching-android-build`.

Agents the skills dispatch:

| Agent | Role | Writes code? |
|---|---|---|
| `lw-architect` | Design / spec for L (or M with design questions) | No |
| `lw-implementer` | One plan task, TDD, one commit | Yes |
| `lw-reviewer` | Two verdicts: spec compliance + code quality; Frappe checklist for Frappe diffs | No |
| `lw-qa` | Regression, negative and offline tests | Tests only |
| `lw-security` | PHI, secrets, auth, storage, logging review | No |
| `lw-release` | Release-readiness checklist | No |
| `lw-frappe-db` | MariaDB/PostgreSQL queries, indexes, patches, backups for the Frappe apps | No |
| `lw-devops` | CI/CD, Docker, Compose, crash loops, rollback diagnosis | No |

### The task loop (L-size)

1. The main session (you + Claude) holds the decisions and dispatches one task at a time.
2. `lw-implementer` does the task: failing test, minimal code, green, one commit.
3. `lw-reviewer` returns two verdicts: `Spec ✅ | Spec ❌` and `Approved | Changes requested`.
   Both must pass (Spec ✅ + Approved). Otherwise findings go back to the implementer.
4. At most **5 fix rounds** per task; then stop and escalate to a human.
5. Each task's brief, report, verdicts and rulings go into a ledger under
   `.superpowers/sdd/<date>-<slug>/` (local working files, gitignored); the plan's ledger table
   records task, commit and verdicts.
6. **Rulings:** when implementer and reviewer disagree, the main session decides and writes the
   ruling with its reason in the ledger. Anything that changes the approved spec goes to a human.
7. After the last task: a **final whole-branch review** by `lw-reviewer` on the strongest model
   against the integration branch, then `/lw-pr`.

### What agents may never do

Merge or approve PRs; push to an integration branch or `main`; force-push; skip hooks (`--no-verify`); tag,
upload or publish a release; set priority, milestones or project fields; change GitHub settings, labels,
Discussion categories or branch protection; create, close or edit issues, Discussions or Wiki pages without an
explicit "yes" from the person; read or stage prod keys, keystores, `key.properties`, `google-services.json`
or `env*.json` (except `env.example.json`); print secrets or patient data; file security issues publicly.
Subagents never spawn agents.

Guard rails enforce most of this: the `.claude/settings.json` hook (`scripts/sdlc/guard_tool.py`) blocks, in Claude
Code, force-push, pushes to integration branches, `--no-verify`, `gh pr merge`, `gh pr review --approve`,
`gh release create|edit|delete|upload`, creating or deleting git tags and pushing tags, `gh api` writes to branch
protection or rulesets, and secret-file access through Bash, Read, Edit, Write and Grep (Glob only lists names and is not guarded).
In Bash that covers commands that print, copy, send or load a secret file (`cat`, `grep`, `sed`, `jq`, `cp`, `curl`,
interpreters, redirects, `git show`) and recursive `grep` or `rg -u`, which would read gitignored files (use `rg` or
`git grep`). Build tools that only consume an env file (`flutter --dart-define-from-file`) are allowed. It is a
best-effort guard on parsed commands, not a sandbox: the real gates are GitHub branch protection and CODEOWNERS,
and other human-only rules (priority, settings, labels) are rules, not hook-enforced. The git hooks in
`.githooks/` check commit messages and block staged secrets. `/lw-setup` points every clone's `core.hooksPath` at leapwell's hooks, which
then chain to the repo's own hooks, so nothing the repo already ran is disabled.

## 11. One-time developer setup

```sh
git clone https://github.com/Medtronic-LABS/leapwell.git && cd leapwell
gh auth login                  # GitHub CLI, used by the lw-* skills
gh auth refresh -s project     # lets /lw-ticket add new issues to Project #4
claude                         # always start Claude from the leapwell root
# then, inside Claude:  /lw-setup
```

`/lw-setup` is backed by `scripts/workspace/setup.sh` (`--only key,key`, `--no-clone`, `--ssh`, `--strict`).
Re-running it is safe: existing clones are only fetched. Run the process checks any time with
`python3 -m unittest discover -s scripts -t .`.

If you had a personal, untracked `.claude/settings.json`, rename it to `.claude/settings.local.json` before
pulling, or git refuses to overwrite it.

Other docs: [TICKETS.md](TICKETS.md) (PM/QA filing guide), [REQUIREMENTS.md](REQUIREMENTS.md) (ideas to sub-issues,
Wiki and mockups), [ADMIN_SETUP.md](ADMIN_SETUP.md) (owner rollout), [REPOS.md](REPOS.md) (repo table).
