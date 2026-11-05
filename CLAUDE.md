# LeapWell hub

`Medtronic-LABS/leapwell` is the home of the LeapWell product team (Apon Sushashthya community health app,
AI Scribe, micro-coaching, Frappe backend, teleconsult integration): requirements, tickets, mockups, and the
shared developer workspace and AI-assisted SDLC for seven code repos. The repo is **public**.

**Start Claude from the leapwell root.** Skills, agents, hooks and settings in `.claude/` only apply there, and
every path below is relative to it. Run `/lw-setup` once to clone the code repos.

Process lives in one place: `docs/process/SDLC.md` (sizes, Definition of Ready/Done, branching, PRs, CI, release).
Also `TICKETS.md` (PM/QA guide), `REQUIREMENTS.md` (Discussions to sub-issues, Wiki and mockup rules),
`ADMIN_SETUP.md` (owner rollout), `REPOS.md` (repo table). Do not copy process rules elsewhere.

## Workspace map

`repos.json` is the single source of repo facts (name, integration branch, verify commands, notes). `/lw-setup`
clones each repo to `repos/<name>` (gitignored, but `.ignore` keeps Grep/Glob searching it).

| Key | `repos/<name>` | Area | Stack |
|---|---|---|---|
| `mobile` | `repos/uhis_lf_mobile` | Mobile app | Flutter |
| `core` | `repos/frappe_spice_next_core` | Frappe apps | Frappe (Python) |
| `shukhee` | `repos/leapwell_shukhee_integration` | Frappe apps | Frappe (Python) |
| `ai` | `repos/leapfrog-ai-service` | AI Scribe | Python FastAPI |
| `coaching` | `repos/spice-coaching` | Micro-coaching | Python |
| `coaching-android` | `repos/spice-coaching-android` | Micro-coaching | Kotlin |
| `coaching-dashboard` | `repos/spice-coaching-dashboard-ui` | Micro-coaching | TypeScript/Vite |

Other folders: `docs/process/` (process), `wiki/` (seed for the GitHub Wiki), `mockups/<feature-slug>/` (design
mockups, fake data only), `env/frappe/` (local Frappe bench built from the workspace clones), `scripts/`
(`sdlc/` checks, `github/` admin scripts, `workspace/` setup, `sync/` thin-layer sync), `templates/repo-layer/`
(what `sync_repos.py` renders into each code repo).

## Ticket model

- **leapwell issues = the what.** Features, bugs, tasks and releases are all filed here by anyone through
  `lw-ticket`. Ideas start as Discussions; the PM promotes agreed ones (`lw-promote`).
- **Code-repo issues = the how.** A developer runs `/lw-route <N>` to create one sub-issue per affected repo,
  linked as GitHub sub-issues, then `/lw-start <repo> <n>` and the S/M/L flow.
- Branch `<type>/<issue#>-<slug>` from the repo's integration branch; PR body `Closes #n` (repo-local sub-issue)
  and `Refs Medtronic-LABS/leapwell#N`. Merging closes the sub-issue; `close-parents` closes the leapwell item.
- Project #4 "LeapWell" tracks both levels. The 412 old `uhis_lf_mobile` issues stay there.

## Skills (`.claude/skills/<name>/SKILL.md`)

Process and hub:

| Skill | Purpose |
|---|---|
| `lw-setup` | Clone/fetch the seven repos into `repos/`, point hooks at `.githooks`, run the tool doctor |
| `lw-ticket` | File a bug, feature, task or release in leapwell through an interview (privacy scrub, preview, create on "yes") |
| `lw-promote` | Promote an agreed Discussion to a leapwell feature issue |
| `lw-route` | Create code-repo sub-issues for a leapwell item and link them |
| `lw-start` | Pick up a sub-issue: Definition of Ready, size, branch, plan comment |
| `lw-fix` | S/M flow: debug, failing test, minimal fix, verify, review |
| `lw-feature` | L flow: brainstorm, spec, plan, subagent task loop, final review |
| `lw-pr` | Run the repo's verify commands, fill the PR template, open a draft PR on "yes" |
| `lw-release` | Release checklist and notes for one repo (never tags or publishes) |
| `lw-wiki` | Edit a page of the live GitHub Wiki (diff, push on "yes") |

Run skills by area (all run builds or services; they only act when invoked):

| Skill | Purpose |
|---|---|
| `lw-mobile-start` | Debug APK build, install and launch on an emulator or device |
| `lw-mobile-fresh-launch` | Clean build, uninstall, install, launch |
| `lw-mobile-e2e` | Playwright end-to-end suite against a Flutter web build |
| `lw-mobile-release` | Release artifact for dev, training or playstore (builds only) |
| `lw-frappe-setup` | First-time or repair setup of the local Frappe bench in `env/frappe` |
| `lw-frappe-start` | Start the bench (`--restart` supported) |
| `lw-frappe-stop` | Stop the bench containers; data kept |
| `lw-frappe-status` | Read-only bench health check |
| `lw-ai-start` | Start the AI Scribe service stack with docker compose |
| `lw-ai-stop` | Stop the AI Scribe containers; database volume kept |
| `lw-ai-status` | Read-only AI Scribe health check |
| `lw-ai-test` | pytest (and optionally ruff) for the AI Scribe service |
| `lw-coaching-start` | Start the micro-coaching backend and/or dashboard dev server |
| `lw-coaching-stop` | Stop them |
| `lw-coaching-status` | Read-only health check of both |
| `lw-coaching-android-build` | Build and test the micro-coaching Android SDK with Gradle |

## Agents (`.claude/agents/`)

Invoke with the Agent tool, `subagent_type: <name>`. The main session is the orchestrator and implementer;
subagents give independent judgement and keep large output out of context. Subagents never spawn agents.

| Agent | Use for |
|---|---|
| `lw-architect` | Design, spec and ADR draft for L-size work in any repo; proposes only |
| `lw-implementer` | One planned task with TDD, one commit on the feature branch |
| `lw-reviewer` | Read-only review: spec compliance + code quality (+ Frappe checklist in `.claude/references/`) |
| `lw-qa` | Write and run tests: regression, negative, offline, e2e; test files only |
| `lw-security` | Read-only security and privacy review (PHI, secrets, auth, storage, logging) |
| `lw-release` | Release-readiness checklist for one repo; never tags or publishes |
| `lw-frappe-db` | MariaDB/PostgreSQL work for the Frappe apps: slow queries, indexes, patches, backups |
| `lw-devops` | CI/CD, Docker, Compose, crash loops, rollback diagnosis; diagnostic-first |

Routing: small change, `lw-reviewer`. New feature or module, `lw-architect` (approve design) then implement, then
`lw-qa` and `lw-reviewer` in parallel. Bug, `systematic-debugging` then `lw-qa` adds the regression test. Slow page
or API, `lw-frappe-db` and `lw-devops`. Auth, db, sync, AI, push, logging, consent or build config, add `lw-security`.

## Human-only gates

Claude proposes; a person decides. Never, without an explicit human step: merge or approve a PR; push to an
integration branch or `main`; force-push; skip hooks; tag, release or upload to a store; set priority, milestones
or Project fields; change GitHub settings, labels, branch protection, Discussion categories or the Wiki outside a
skill that shows a diff and waits for "yes"; touch prod keys, keystores, `key.properties`, `google-services.json`
or `env*.json` (except `*.example`); create, edit or close issues without a preview and an explicit "yes".
`scripts/github/*.sh` and `sync_repos.py` are dry-run by default; `--apply` only when asked. The
`.claude/settings.json` guard hook blocks PR merge/approve, releases, tags, force-push, protected-branch pushes,
branch-protection API writes and secret-file access; `.githooks/` check commits. Other gates are rules, backed by
GitHub branch protection.

## Privacy rules (public repo)

No patient or member data, names, phone numbers, IDs, addresses, credentials, tokens, env values, hostnames of
internal systems or unscrubbed logs in code, docs, issues, Discussions, Wiki, mockups, PRs, commits or tests.
Mockups and tests use fake data only. Scrub before any write to GitHub (the `lw-*` skills do this with
`scripts/sdlc/patterns.py`); security problems go to a private advisory, never a public issue. Do not copy
secrets or env values out of other repos. CI (`secret-scan`, `mockup-scan`, `pr-check`) enforces this.

## Conventions

- Repo facts come from `repos.json` only (DRY); PHI and secret patterns from `scripts/sdlc/patterns.py`; process
  from `docs/process/SDLC.md`.
- Python in `scripts/` is stdlib-only (3.11+) with unit tests: `python3 -m unittest discover -s scripts -t .`.
- Lint rules live in `repos.json` (`lint_rules`, `hub_lint_rules`); the pre-commit hook and CI both run them through
  `scripts/sdlc/lint_files.py` on changed files only. A failure or a missing tool blocks the commit.
  Shell scripts use `set -euo pipefail` and are dry-run by default.
- Commits: Conventional Commit subject, issue as `(#N)`. Branches `<type>/<issue#>-<slug>`.

## Engineering Design Standards

Canonical engineering doctrine for **all code in this workspace** — every LeapWell repo cloned under `repos/`
(including the `uhis_lf_mobile` Flutter app) and any service scaffolded from a spec — and the standard every
command, agent, skill, and review gate must enforce. **Reference this section by name** ("Engineering Design
Standards"); do not copy these rules into other files — that duplication is itself the anti-pattern we forbid.

- **OOP & SOLID.** Cohesive types, one responsibility each. Depend on abstractions, not concretions. Prefer composition over inheritance; keep hierarchies shallow. No god-objects; no business logic in data classes.
- **DRY / reuse.** Every literal, rule, and behavior has exactly one home. Search for an existing helper / constant / service before writing new code; logic in 2+ places gets extracted. In-tree exemplar: UI copy → `repos/uhis_lf_mobile/lib/core/constants/app_strings.dart`; build-time env → `AppConfig`.
- **Modularity & separation of concerns.** Layer strictly: UI ↔ state/domain ↔ repository/data ↔ transport. Widgets carry no business logic or raw I/O; repositories carry no UI; the HTTP / FHIR client sits behind an interface. Mirror the layered topology in the architecture reference of the leapfrog-setup design workspace (§3).
- **Abstraction.** Program to contracts, not wiring. Core services speak **FHIR R4 on the wire — no bespoke DTOs cross service boundaries** (§3.3 of that architecture reference).
- **Configuration management.** No hardcoded URLs, keys, secrets, ports, or env values in source. Inject all config (`--dart-define` / env / `.env`) behind a single typed accessor (`AppConfig`). Defaults exist only to keep local dev running.
- **Localization.** No hardcoded user-facing strings in any screen / widget. All copy lives in the centralized content-constants module (`app_strings.dart`), grouped by feature, exposed as constants + static helpers for interpolation. That module is the single localization seam — a new language is a lookup swap, not an edit sweep (§3.1).
- **Error handling.** Fail explicitly, at the right layer. Catch narrow exception types — never a bare `catch (_)` that swallows. Repositories throw typed domain exceptions; UI maps them to **localized** messages and logs diagnostics separately. Never leak raw stack traces or internal IDs to users. Degrade gracefully offline (§3.1 offline contract).
- **Maintainability.** New code reads like its neighbors. Small, intention-revealing functions; no dead or commented-out code. New public behavior ships with a test. Keep rendered UI strings stable so e2e selectors hold.
- **Scalability.** Design for pilot → state → national (§7). Stateless services where possible; bounded queries (pagination / caps); no N+1 fan-out; offline-first edge with conflict-aware sync (§5.4).

Flutter-specific standards for `uhis_lf_mobile` (technology stack, folder structure, DI chain, coding
constraints, design tokens, security model, three-tier testing) are in the leapfrog-setup design workspace's
Flutter standards document; the app's own `CLAUDE.md` in `repos/uhis_lf_mobile` covers its current layout.

**Enforcement.** Code-authoring skills apply these standards; the review gates (`lw-reviewer`, `lw-architect`,
`lw-security`) flag violations as findings. A change that introduces duplication, a hardcoded string, leaked
configuration, or a swallowed error is **not done**.
