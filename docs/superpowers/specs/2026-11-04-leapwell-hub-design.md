# LeapWell hub repo — design

Date: 2026-11-04 · Owner: LeapWell engineering lead · Repo: `Medtronic-LABS/leapwell` (public)

## 1. Intent

`leapwell` is the single home for the LeapWell product team:

1. **Requirements management** — ideas in Discussions, project/feature knowledge in the Wiki,
   mockups as files in the repo, all tickets in leapwell Issues tracked on org Project #4 "LeapWell".
2. **Developer workspace** — a developer clones leapwell, starts Claude CLI in it and runs
   `/lw-setup`; that clones the seven LeapWell code repos inside it and wires them up. Claude
   commands, agents and skills for every LeapWell stack live here once — not copied into each repo.
3. **AI-SDLC** — the process built in `uhis_lf_mobile` PR #744 (S/M/L sizing, Definition of
   Ready/Done, multi-agent plan → implement → review loop, guard hook, git hooks, CI gates, human-only
   gates) moves here and applies to all seven repos.

Why: today the rules, tickets and Claude setup live in `uhis_lf_mobile` and the Bitbucket
`platform-setup` repo (which mixes LeapWell with the UHIS/SPICE Java stack). The team wants one place
that PM, QA and developers all use, and one copy of the rules that every repo follows.

## 2. Scope

### Repos covered (manifest `repos.json`)

| Key | GitHub repo | Area | Stack | Integration branch |
|---|---|---|---|---|
| `mobile` | `uhis_lf_mobile` | Mobile app | Flutter | `develop` |
| `core` | `frappe_spice_next_core` | Frappe apps | Frappe (Python) | `main` |
| `shukhee` | `leapwell_shukhee_integration` | Frappe apps | Frappe (Python) | `main` |
| `ai` | `leapfrog-ai-service` | AI Scribe / briefing | Python FastAPI | `develop` |
| `coaching` | `spice-coaching` | Micro-coaching backend + SDK | Python | `leapwell-main` |
| `coaching-android` | `spice-coaching-android` | Micro-coaching Android SDK/app | Kotlin | `leapwell-main` |
| `coaching-dashboard` | `spice-coaching-dashboard-ui` | Micro-coaching dashboard | TypeScript/Vite | `leapwell-main` |

All under the `Medtronic-LABS` org. Integration branches are the builder's starting values, read from
GitHub branch lists on 2026-11-04 — the manifest is the single place to correct them.

### Non-goals

- UHIS / SPICE Java services (`uhis-platform/*`, spice-service, fhir-*, etc.) — not set up, no commands.
- Leapfrog design-layer commands (`leapfrog-*` spec/FHIR/journey tooling) — stay in `platform-setup`.
- Migrating the 412 existing `uhis_lf_mobile` issues — they stay where they are.
- Changing anything on GitHub directly (labels, Discussion categories, Wiki, Project fields, branch
  protection, other repos' PRs). Every such change ships as a script that is dry-run by default.

### Anti-goals (would be failure even if it works)

- Patient data, real names, partner-confidential details, tokens or env values in the public repo,
  its Discussions, Wiki, mockups or issues.
- The rules drifting: two different copies of the SDLC logic that disagree.
- QA/PM having to know which repo a bug belongs to.
- Claude creating, closing or merging anything on GitHub without an explicit human "yes".

## 3. Ticket model (decided)

Two levels.

- **leapwell Issues = the "what".** Requirements/features, tasks, bugs and releases are all filed in
  leapwell by anyone (PM, QA, dev) through the `lw-ticket` skill (Claude CLI or claude.ai/Desktop chat
  via the org skill). Types and required sections are the PR #744 contract (bug, feature, task,
  release). Bug gains an optional "Repo or component (if known)" field — QA may leave it blank.
- **Code-repo Issues = the "how".** A developer triages a leapwell item with `/lw-route <N>`: Claude
  reads it, proposes one sub-issue per affected repo (title, body with repro / acceptance criteria and
  a back-link), and on "yes" creates them in the code repos and links them as **sub-issues** of the
  leapwell item (GitHub REST `POST /repos/{owner}/{repo}/issues/{n}/sub_issues`, cross-repo within the
  org). The leapwell item gets label `status:routed`. One skill covers bugs and features/tasks.
- **Developers work locally.** Branch `<type>/<N>-<slug>` from the repo's integration branch, PR body
  `Closes #N` with the repo-local sub-issue number. `pr-check` also accepts
  `Closes|Refs Medtronic-LABS/leapwell#N` (for small chores without a sub-issue).
- **Auto-close.** A scheduled workflow in leapwell (`close-parents`, hourly) closes an open leapwell
  item labelled `status:routed` whose sub-issues are ≥1 and all closed, with a comment listing them.
  GitHub does not do this natively and events from code repos cannot trigger leapwell workflows.
- **Project #4** shows both levels; its built-in Repository field separates them. leapwell is added
  to the project by `setup_project.sh` (dry-run default).
- **Issues stay enabled in code repos** (sub-issues need them). Their issue chooser points people to
  leapwell (`config.yml` contact link); blank issues remain allowed so developers and `/lw-route` can
  create sub-issues.

## 4. Requirements flow (decided)

1. **Discussions = ideas.** Categories: *Ideas*, *Field feedback*, *Partner requests*, *Q&A*,
   *Announcements*. Discussion forms (`.github/DISCUSSION_TEMPLATE/*.yml`) for the first three.
   Categories cannot be created through the API — `setup_discussions.sh` prints the UI steps and
   checks which exist.
2. **Promotion.** When an idea is agreed, PM runs `/lw-promote <discussion#>`: Claude reads the
   discussion, runs the `lw-ticket` feature interview for what's missing (user, problem, acceptance
   criteria, programme, offline behaviour, privacy), previews, creates the leapwell feature issue on
   "yes" with a link back, and comments on the discussion with the issue link. Privacy scrub applies.
3. **Wiki = the project and its features.** Pages: Home, Project overview, Repos & areas, one page
   per feature area (AI Scribe, Visit briefing, Micro-coaching, Visit flow & CDSS, Teleconsult
   (Shukhee), Household & enrolment, Sync & offline), Glossary. Seeded from `wiki/` in the repo by
   `publish_wiki.sh` (refuses to overwrite a non-empty wiki unless `--force`). After seeding, the
   GitHub Wiki is the live copy; `/lw-wiki <page>` clones it, edits, shows the diff and pushes only on
   "yes". Process docs (SDLC, tickets, requirements flow, admin setup) live in `docs/process/` in the
   repo (PR-reviewed), and the Wiki links to them.
4. **Mockups** live in `mockups/<feature-slug>/` (HTML, PNG, SVG, PDF) with a `README.md` per
   feature linking its leapwell issue. Added by PR. Fake data only; a CI check scans mockup text
   files with the PHI patterns.

## 5. Workspace and Claude setup (decided)

- Developers clone leapwell and start Claude **from the leapwell root**. `/lw-setup` (skill backed by
  `scripts/workspace/setup.sh`) clones or fast-forwards each repo from `repos.json` into `repos/<repo>`
  (gitignored), sets each repo's `core.hooksPath` to leapwell's `.githooks`, and checks tools
  (git, gh + auth, python3 ≥3.11, flutter, docker, node, java) reporting what's missing per area.
  Re-running is safe.
- One copy of everything Claude: `CLAUDE.md` (workspace map, rules, Engineering Design Standards for
  LeapWell — this file becomes their home for LeapWell code), `.claude/agents`, `.claude/skills`,
  `.claude/settings.json` (guard hook). The rule "start Claude from the leapwell root" is stated in
  `CLAUDE.md`, the README and each code repo's thin layer.
- **Area skills** (ported from `platform-setup`, paths rewritten to `repos/<repo>`, all
  `disable-model-invocation: true` where they run builds or deploy):
  - Mobile: `lw-mobile-start`, `lw-mobile-fresh-launch`, `lw-mobile-e2e`, `lw-mobile-release`
    (dev / training / playstore as an argument; replaces the three `lf_release_*` commands).
  - Frappe: `lw-frappe-setup`, `lw-frappe-start`, `lw-frappe-stop`, `lw-frappe-status`, backed by
    `env/frappe/` (docker compose + setup script ported from `uhis-next/frappe-uhis-next`) that installs
    `repos/frappe_spice_next_core` and `repos/leapwell_shukhee_integration` into the bench from the
    workspace (bind mount / editable install) instead of scaffolding them.
  - AI Scribe: `lw-ai-start`, `lw-ai-stop`, `lw-ai-status`, `lw-ai-test` over the service's own
    docker compose / pytest.
  - Micro-coaching: `lw-coaching-start`, `lw-coaching-stop`, `lw-coaching-status` (backend compose,
    dashboard dev server) and `lw-coaching-android-build`.
- **Agents** (one set, all `lw-`): from PR #744 `lw-architect`, `lw-implementer`, `lw-reviewer`,
  `lw-qa`, `lw-security`, `lw-release`, generalised to every stack in `repos.json`; plus
  `lw-frappe-db` and `lw-devops` ported from `platform-setup`'s `frappe-db-engineer` and `devops-sre`.
  `solution-architect`, `qa-engineer`, `frappe-code-reviewer` are folded into lw-architect, lw-qa and
  lw-reviewer (Frappe checklist kept as a reference file the reviewer reads for Frappe diffs).
- **Workflow skills** from PR #744 (`lw-start`, `lw-fix`, `lw-feature`, `lw-pr`, `lw-release`) become
  repo-aware: they take or infer the repo, read its integration branch and verify commands
  (test/lint/build) from `repos.json`, and branch inside `repos/<repo>`.

## 6. Keeping the code repos in line (decided)

- What GitHub only reads from the repo itself is a **thin per-repo layer**: `pr-check` workflow,
  `secret-scan` workflow, PR template, `CODEOWNERS`, `ISSUE_TEMPLATE/config.yml` (points to leapwell),
  and a short `CLAUDE.md` pointer section ("start Claude from leapwell").
- The thin workflows contain no logic: they check out `Medtronic-LABS/leapwell` at a pinned ref and run
  its `scripts/sdlc/*.py`. Logic stays in leapwell; bumping the pin is the update.
- `scripts/sync/sync_repos.py` renders the layer from `templates/repo-layer/` per repo using
  `repos.json` and shows a diff (default, dry-run). `--apply` writes it on a local branch
  `chore/leapwell-sync` inside `repos/<repo>` and commits; it never pushes or opens PRs (a human does).
  It never overwrites a repo's existing build/test CI; it only owns the files above, and merges into
  an existing `CLAUDE.md` / `config.yml` by a marked section.
- Build/test CI per stack stays in each repo as today (mobile's from PR #744).

## 7. PR #744 (`uhis_lf_mobile`)

Slim it to match: remove the ticket-filing half (issue forms bug/feature/task/release, `issue-check`
workflow, `lw-ticket` skill, `TICKETS.md`, ticket parts of `CLAUDE_ADMIN_SETUP.md`), replace
`config.yml` with the leapwell pointer + blank issues allowed, make `pr-check` accept leapwell refs,
point `CLAUDE.md` / `SDLC.md` at leapwell. Push to `chore/sdlc-ticketing`, PR stays draft. Its
developer toolkit (agents, workflow skills, guard hook, `scripts/sdlc`) is left in place for now —
removing it once leapwell is merged is a follow-up for the owner.

## 8. Constraints

- Public repo: privacy scrub on every Claude-written ticket, promotion, route and wiki edit (PR #744
  `patterns.py`); secret-scan (gitleaks CLI `--redact`) in CI; mockups fake data only.
- No secrets or env values ported from `platform-setup` (hash keys, tokens, admin passwords, backend
  URLs that are not already public). Local-dev defaults come from `*.example` files.
- Stdlib-only Python ≥3.11, unit-tested (`python3 -m unittest discover -s scripts -t .`); shell
  scripts `set -euo pipefail`, dry-run by default, `--apply` to act.
- Human-only: merge, push to protected branches, tag/release, priority, prod keys, GitHub settings.
- Engineering Design Standards apply (DRY: one home per rule — `repos.json` for repo facts,
  `patterns.py` for PHI/secret patterns, `docs/process/SDLC.md` for process).

## 9. Delivery and rollout

1. Seed `main` with README + `.gitignore`; everything else on `chore/leapwell-hub` → draft PR.
2. Owner reviews/merges; runs `sync_labels.sh`, `setup_discussions.sh`, `setup_project.sh`,
   `publish_wiki.sh`, `protect_branches.sh` (dry-run then `--apply`); uploads the `lw-ticket` org
   skill (re-packaged from leapwell).
3. `sync_repos.py --apply` per repo → owner pushes and opens PRs.
4. Announce to PM/QA: file everything in leapwell.

## 10. Calls made after the builder check (owner to confirm)

1. **Closing sub-issues on the integration branch.** Every repo's default branch is `main`, so
   GitHub ignores `Closes #N` on merges into `develop` / `leapwell-main`. The thin layer adds
   `lw-close-on-merge.yml`: on a merged PR into the repo's integration branch it closes the local
   issues named by `Closes|Fixes|Resolves #N` (GITHUB_TOKEN, `issues: write`).
2. **Private repo.** `leapfrog-ai-service` is private (the other six are public). `close-parents`
   uses secret `LEAPWELL_BOT_TOKEN` (fine-grained PAT or App token: issues read on the seven repos,
   issues write on leapwell), falling back to `GITHUB_TOKEN`. A sub-issue it cannot read blocks the
   close (fail safe). Owner provisions the secret.
3. **Routing completeness.** `/lw-route` adds `status:routed` only after the developer confirms routing
   is complete; more sub-issues can still be added later. Sub-issues closed as "not planned" count as
   closed. Items never routed (docs, releases, chores done in leapwell) are closed by hand or by a
   leapwell PR.
4. **Existing hooks.** leapwell's git hooks run their checks and then chain to the repo's own hooks
   (`.githooks/<hook>` in the repo, then `$GIT_DIR/hooks/<hook>`, e.g. the pre-commit framework's),
   so setting `core.hooksPath` disables nothing. `core.hooksPath` is set to an absolute path.
5. **Search inside `repos/`.** `repos/` is git-ignored, which Claude's Grep/Glob (ripgrep) would skip;
   leapwell ships a `.ignore` with `!/repos/` so they still search the clones.
6. **Duplicate search.** `lw-ticket` searches leapwell and the legacy `uhis_lf_mobile` issues.
7. **Pin.** Thin workflows check out leapwell at `main` until the owner creates a tag; `sync_repos.py
   --ref` changes it everywhere.
8. **Scheduled-workflow keep-alive.** GitHub disables cron workflows after 60 days without repo
   activity; `close-parents` also has `workflow_dispatch`, and ADMIN_SETUP notes the risk.
9. **Frappe env** is the MariaDB-based bench from `uhis-next/frappe-uhis-next`, unchanged except that
   both apps come from the workspace clones.
10. **Wiki bootstrap.** The wiki's git remote exists only after a first page is created in the UI;
    `publish_wiki.sh` detects that and prints the step.

## 11. Left to the builder

File-level layout inside each folder, exact wording of docs and skills, test design, Discussion form
fields, how `env/frappe` mounts apps (bind mount vs. copy) as long as the workspace clones are the
source, how `close-parents` paginates.
