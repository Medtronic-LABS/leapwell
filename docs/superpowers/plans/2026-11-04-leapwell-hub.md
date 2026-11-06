# LeapWell hub repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the empty `Medtronic-LABS/leapwell` repo into the LeapWell requirements home, developer workspace and shared AI-SDLC for seven code repos, and slim `uhis_lf_mobile` PR #744 to match.

**Architecture:** Port the PR #744 toolkit (stdlib-Python `scripts/sdlc`, admin shell scripts, Claude agents/skills, git hooks, GitHub config) into leapwell, make it repo-aware through one manifest `repos.json`, add requirements tooling (Discussions forms, wiki seed, mockups, `lw-promote`, `lw-route`, `lw-wiki`, `close-parents`), port area run commands from `platform-setup`, and add a sync script that renders a thin, logic-free layer into each code repo.

**Tech Stack:** Python ≥3.11 stdlib + unittest, bash, GitHub Actions, gh CLI, Claude Code skills/agents/hooks.

**Spec:** `docs/superpowers/specs/2026-11-04-leapwell-hub-design.md`

**Paths used below:**
- `L` = leapwell clone (this repo): `/Users/amresh/labs/UHIS/leapfrog-setup/uhis_lf_mobile/.claude/worktrees/sdlc-ticketing/.superpowers/leapwell`
- `S` = PR #744 source toolkit: `/Users/amresh/labs/UHIS/leapfrog-setup/uhis_lf_mobile/.claude/worktrees/sdlc-ticketing`
- `P` = platform-setup: `/Users/amresh/labs/UHIS` (`.claude/commands`, `.claude/agents`, `.claude/skills/release-check`, `uhis-next/frappe-uhis-next`)

## Global Constraints

- Public repo: no patient data, real names, tokens, hash keys, passwords other than documented local-dev placeholders, or non-public backend URLs. When porting from `P`, replace any such value with a reference to an env/example file.
- Python: stdlib only, ≥3.11; tests run with `python3 -m unittest discover -s scripts -t .` from `L`; every CLI runs as `python3 scripts/<pkg>/<x>.py` and `python3 -m scripts.<pkg>.<x>`.
- Shell: `#!/usr/bin/env bash`, `set -euo pipefail`; anything that changes GitHub or another repo is dry-run by default and acts only with `--apply`.
- Claude never merges, pushes to protected branches, tags, releases, sets priority, or creates/edits GitHub content without an explicit "yes" in the conversation. Skills that file/route/promote/edit wiki show a full preview first.
- One home per fact: repo facts only in `repos.json`; PHI/secret patterns only in `scripts/sdlc/patterns.py`; process only in `docs/process/SDLC.md`; CI budgets only in each repo's own workflow.
- All Claude assets use the `lw-` prefix. Skills that build, deploy or touch GitHub set `disable-model-invocation: true`.
- Org `Medtronic-LABS`; tracker repo `Medtronic-LABS/leapwell`; Project #4 "LeapWell".
- Commit messages: Conventional Commits; end with the two attribution lines given by the controller.

## Review Focus

1. PR body referencing `Medtronic-LABS/leapwell#12` from a code repo must pass `pr-check`; `leapwell#12` without owner and `#12` with only a leapwell intent are handled per Task 1 tests.
2. `close-parents` must never close an item with zero sub-issues, with any open sub-issue, or without `status:routed`.
3. `sync_repos.py` on a repo that already has `CLAUDE.md` / `ISSUE_TEMPLATE/config.yml` must only replace its marked section and leave the rest byte-identical; second run is a no-op.
4. Guard hook run from the leapwell root must block `git -C repos/<x> push origin <integration-branch>` and `cd repos/<x> && git push origin main` for every repo's protected branches from `repos.json`.
5. Ported area skills must contain no secrets/env values (secret-scan + `find_sensitive` test over `.claude/`).

---

### Task 1: SDLC core scripts, repos manifest, close-parents

**Files:**
- Create: `repos.json`, `scripts/__init__.py`, `scripts/sdlc/{__init__,patterns,check_issue,check_pr,ci_budget,commit_msg,guard_staged,guard_tool,repos,close_parents}.py`, `scripts/sdlc/tests/…`
- Port from `S/scripts/sdlc` (copy, then change as below), with their tests.

**Interfaces — Produces:**
- `repos.json`: `{"org": "Medtronic-LABS", "tracker": "leapwell", "project": 4, "repos": [{"key","name","area","stack","integration_branch","protected_branches":[…],"verify":{"test","lint","build"}}]}` with the 7 repos from spec §2 (protected = integration branch + `main`, deduplicated; verify commands from each repo's README/CLAUDE.md — mobile `flutter test` / `flutter analyze`, python repos `pytest` (or `python -m pytest`), frappe repos `bench --site <site> run-tests --app <app>` noted as needing the frappe env, dashboard `npm run lint` / `npm run build`, android `./gradlew test`).
- `scripts/sdlc/repos.py`: `load(path=None) -> Manifest`; `Manifest.repos`, `Manifest.by_key(k)`, `Manifest.by_name(n)`, `Manifest.protected_branches() -> set[str]` (union), `Manifest.tracker_slug -> "Medtronic-LABS/leapwell"`. Validates required keys, raises `ValueError` naming the bad entry.
- `patterns.py`: `ISSUE_REF_RE` accepts `<kw> #N` and `<kw> Medtronic-LABS/leapwell#N` (kw = close/closes/closed/fix…/resolve…/ref/refs); `TRACKER_REF_RE` for the cross-repo form only. Bug `REQUIRED_SECTIONS` unchanged (repo field optional, not required).
- `guard_tool.py`: protected branches come from `repos.Manifest.protected_branches()` (fallback `{"main","develop"}` if manifest missing); detects pushes from `git -C <path>` and `cd <path> && git …` forms already handled by the S parser — extend tests for repos/ paths.
- `close_parents.py`: pure `decide(parent: dict, subs: list[dict], unreadable: int = 0) -> bool` (True only if parent open, has label `status:routed`, len(subs) ≥ 1, `unreadable == 0`, and all subs `state == "closed"` — any `state_reason`, so "not planned" counts); token from env `GH_TOKEN` (workflow sets it from `LEAPWELL_BOT_TOKEN` or falls back to `GITHUB_TOKEN`); a sub-issue fetch error counts as unreadable; `main(argv)` with `--repo Medtronic-LABS/leapwell`, `--dry-run` default true via `--apply` flag; lists open issues labelled `status:routed` via `gh api --paginate`, fetches `GET /repos/{o}/{r}/issues/{n}/sub_issues`, closes with a comment listing sub-issue URLs only on `--apply`. gh calls go through one injectable `run_gh(args) -> str` so tests use a fake.

- [ ] Step 1: Copy S scripts/sdlc + tests; make tests pass unchanged from `L` (`python3 -m unittest discover -s scripts -t .`).
- [ ] Step 2: Write failing tests: `test_repos.py` (loads real repos.json, 7 repos, unique keys/names, every protected set contains the integration branch, bad entry → ValueError), `test_patterns.py` additions (`Closes Medtronic-LABS/leapwell#12` ok, `Refs Medtronic-LABS/leapwell#7` ok, `Closes Medtronic-LABS/other#1` not a tracker ref), `test_check_pr.py` cross-repo body passes, `test_guard_tool.py` (`git -C repos/spice-coaching push origin leapwell-main` denied, `cd repos/uhis_lf_mobile && git push origin develop` denied, feature push allowed), `test_close_parents.py` (the five Review Focus #2 cases + happy path; `--apply` absent → no close call).
- [ ] Step 3: Implement; Step 4: all tests pass; Step 5: commit `feat(sdlc): core scripts, repos manifest, close-parents`.

### Task 2: leapwell GitHub layer and admin scripts

**Files:** `.github/ISSUE_TEMPLATE/{bug,feature,task,release,config}.yml`, `.github/DISCUSSION_TEMPLATE/{ideas,field-feedback,partner-requests}.yml`, `.github/pull_request_template.md`, `.github/CODEOWNERS`, `.github/labels.yml`, `.github/workflows/{ci,issue-check,pr-check,close-parents}.yml`, `scripts/github/{lib,sync_labels,setup_project,setup_discussions,publish_wiki,protect_branches,package_skill}.sh`, tests `scripts/sdlc/tests/test_github_config.py`, `test_admin_scripts.py`.

**Interfaces — Consumes:** Task 1 CLIs and `repos.json`. **Produces:** label names (`type:bug|feature|task|release`, `status:needs-info`, `status:routed`, `status:triage`, `area:<repo key>` for each repo in repos.json, plus S labels), job names `sdlc-scripts`, `secret-scan`, `mockup-scan`, `pr-check`.

- Issue forms: port S forms; bug adds optional dropdown "Repo or component (if known)" with options from repos.json areas + "Don't know"; `config.yml` blank issues off, contact link to Discussions for ideas.
- Discussion forms: fields for Ideas (problem, who, idea, evidence, privacy check), Field feedback (where/when, what happened, impact, privacy check), Partner requests (partner type — not name, request, deadline, privacy check).
- `ci.yml`: `sdlc-scripts` (unittest), `secret-scan` (gitleaks CLI 8.24.3 `--redact`, as S), `mockup-scan` (runs `find_sensitive` over text files under `mockups/` and `wiki/`). `close-parents.yml`: `schedule: cron '17 * * * *'` + `workflow_dispatch`, `permissions: issues: write`, runs `close_parents.py --apply`.
- Admin scripts (dry-run default): `sync_labels.sh` (leapwell; `--all-repos` also code repos from repos.json), `setup_project.sh` (add leapwell to Project #4, ensure Priority/Type fields, print Status UI steps — never mutate Status), `setup_discussions.sh` (enable check + list existing categories via GraphQL, print UI steps for missing), `publish_wiki.sh` (clone `<repo>.wiki.git` to a temp dir; refuse if non-empty without `--force`; copy `wiki/*.md`; commit; push only with `--apply`; print the "create first page in UI" step if the wiki repo doesn't exist yet), `protect_branches.sh` (leapwell `main`; required checks sdlc-scripts, secret-scan, mockup-scan), `package_skill.sh` (zip `.claude/skills/lw-ticket` → `dist/skills/lw-ticket.zip`).
- Tests: forms carry the required headings from `REQUIRED_SECTIONS`; label names referenced in workflows/skills exist in labels.yml; every admin script supports `--help` and does nothing mutating without `--apply` (fake `gh` on PATH records calls).
- Commit `feat(github): leapwell issue/discussion forms, workflows, admin scripts`.

### Task 3: Workspace setup, guard hook, git hooks

**Files:** `scripts/workspace/setup.sh`, `scripts/workspace/doctor.py` (tool check, testable), `.claude/settings.json`, `.githooks/{commit-msg,pre-commit}`, tests `test_workspace.py`.

- `setup.sh [--only key,…] [--no-clone]`: for each repo in repos.json (read via `python3 -m scripts.sdlc.repos --list` — add that CLI in this task), clone `https://github.com/<org>/<name>.git` into `repos/<name>` if missing (checkout integration branch), else `git fetch` + report (never reset/rebase a dirty clone); set `core.hooksPath` to absolute `<L>/.githooks` per clone; run `doctor.py`.
- `doctor.py`: per area which tools are required (mobile: flutter, java; frappe: docker; ai: docker or python3; coaching: docker, node, java), checks via `shutil.which` + version for python; prints a table; exit 0 always (informational) unless `--strict`.
- `.githooks`: port S hooks; they must work when invoked from any `repos/<x>` clone (resolve leapwell root from the hook's own path, not cwd). After leapwell's own check passes, chain to the repo's own hook: `<repo>/.githooks/<hook>` if executable, else `$(git rev-parse --git-path hooks)/<hook>` if executable (pre-commit framework), passing args/stdin through; a failing chained hook fails the commit.
- `.ignore` at leapwell root containing `!/repos/` (so ripgrep-based Claude Grep/Glob search the git-ignored clones); test with `rg --files` if rg is installed, else skip.
- `.claude/settings.json`: S hook matcher `Bash|Read|Edit|Write|Grep` → `python3 "$CLAUDE_PROJECT_DIR"/scripts/sdlc/guard_tool.py`.
- Tests: hooks resolve root from their path (run commit-msg hook in a temp git repo with hooksPath pointed at L/.githooks); setup.sh `--help` and a `--no-clone` dry pass using a temp manifest (`LW_REPOS_JSON` env override) touch nothing.
- Commit `feat(workspace): lw-setup script, doctor, hooks`.

### Task 4: Claude agents and SDLC/ticket skills

**Files:** `.claude/agents/lw-{architect,implementer,reviewer,qa,security,release,frappe-db,devops}.md`, `.claude/agents/references/frappe-review-checklist.md`, `.claude/skills/{lw-setup,lw-ticket,lw-route,lw-promote,lw-wiki,lw-start,lw-fix,lw-feature,lw-pr,lw-release}/SKILL.md` (+ `lw-ticket/references/*`), test `test_claude_toolkit.py`.

- Port S agents/skills; generalise every Flutter-only instruction to "the repo's verify commands from repos.json". Fold `P/.claude/agents/{solution-architect,qa-engineer,frappe-code-reviewer}.md` content into lw-architect / lw-qa / lw-reviewer (+ checklist reference); port `frappe-db-engineer` → `lw-frappe-db`, `devops-sre` → `lw-devops`.
- `lw-ticket`: files into `Medtronic-LABS/leapwell`; duplicate search covers leapwell and legacy `Medtronic-LABS/uhis_lf_mobile` issues; adds `area:<key>` label only if the reporter knew it; otherwise `status:triage`.
- `lw-route <N>`: read leapwell issue (`gh issue view -R Medtronic-LABS/leapwell N --json …`), propose sub-issues per repo (from repos.json areas), privacy-scrub with `scripts/sdlc/check_issue.py`, preview, on "yes": `gh issue create -R <org>/<repo>` then link via `gh api -X POST repos/Medtronic-LABS/leapwell/issues/N/sub_issues -F sub_issue_id=<database id from gh api repos/<org>/<repo>/issues/<n> --jq .id>`; ask "Is routing complete for this item?" and only on yes add `status:routed` (remove `status:triage`); add created issues to Project #4 (`gh project item-add 4 --owner Medtronic-LABS --url …`).
- `lw-promote <discussion#>`: read via `gh api graphql` (discussion title/body/comments/url), run the lw-ticket feature interview for gaps, preview, create feature issue on yes, comment on discussion with the link.
- `lw-wiki <page>`: clone wiki to a temp dir, edit, show diff, push only on yes; scrub.
- `lw-setup`: runs `bash scripts/workspace/setup.sh` and explains the doctor table.
- `lw-start/fix/feature/pr/release`: take `<repo-key> <N>` (or infer repo from cwd under `repos/`), branch from the repo's integration branch, run its verify commands, PR body `Closes #N` (sub-issue) or `Refs Medtronic-LABS/leapwell#N`.
- Tests (port S `test_claude_toolkit.py`): frontmatter valid, names match folders, `disable-model-invocation: true` on lw-route/lw-promote/lw-wiki/lw-release/lw-setup, every skill/agent mentioning a repo key uses one in repos.json, no `find_sensitive` hits in `.claude/`.
- Commit `feat(claude): lw agents and SDLC, ticket, routing, promotion and wiki skills`.

### Task 5: Area run skills and Frappe env

**Files:** `.claude/skills/lw-mobile-{start,fresh-launch,e2e,release}/SKILL.md`, `lw-frappe-{setup,start,stop,status}`, `lw-ai-{start,stop,status,test}`, `lw-coaching-{start,stop,status,android-build}`, `env/frappe/{docker-compose.yml,frappe_setup.sh,.env.example,README.md}` (+ any small files the compose needs from `P/uhis-next/frappe-uhis-next/docker`), test additions in `test_claude_toolkit.py`.

- Mobile: port `P/.claude/commands/lf-mobile-{start,fresh-launch,e2e}.md` and merge `lf_release_{dev,training,playstore}.md` into `lw-mobile-release` (argument `dev|training|playstore`); paths → `repos/uhis_lf_mobile`; env files referenced by name only (`env.<flavor>.json`, gitignored in the app repo); remove literal hash keys/URLs/credentials.
- Frappe: port `frappe_setup.sh` + compose to `env/frappe/`; replace the "scaffold shukhee_integration / app source inside bench tree" steps with installing from the workspace clones (`repos/frappe_spice_next_core`, `repos/leapwell_shukhee_integration`) via bind mounts into `apps/`; admin password and site name from `env/frappe/.env` (`.env.example` holds local-dev placeholders); keep `--start/--stop/--status/--restart`. `bash -n` must pass; `--help` must run without docker.
- AI: skills drive `repos/leapfrog-ai-service` (`docker compose up -d`, `/health` check, `pytest`), env from its `env.example`.
- Coaching: read `repos`' READMEs via `gh api repos/Medtronic-LABS/<name>/readme` (workspace may not be cloned yet) and write skills that use each repo's documented commands; mark any command not found in a README as "check the repo README" rather than inventing it.
- Tests: every area skill names only paths under `repos/<name>` for names in repos.json; `bash -n env/frappe/frappe_setup.sh`; no sensitive hits.
- Commit `feat(claude): area run skills and frappe dev env`.

### Task 6: Repo sync (thin per-repo layer)

**Files:** `templates/repo-layer/{pr-check.yml,secret-scan.yml,close-on-merge.yml,pull_request_template.md,CODEOWNERS,issue-config.yml,claude-section.md}`, `scripts/sdlc/close_on_merge.py` (+ test), `scripts/sync/{__init__,sync_repos}.py`, `scripts/sync/tests/test_sync_repos.py`.

- Templates use `{{org}}`, `{{tracker}}`, `{{repo}}`, `{{integration_branch}}`, `{{leapwell_ref}}` placeholders (simple `str.replace`, no Jinja). `pr-check.yml` / `secret-scan.yml` check out `Medtronic-LABS/leapwell` at `{{leapwell_ref}}` into `.leapwell/` and run its scripts. `CODEOWNERS` default `* @Medtronic-LABS/leapfrogging`.
- `sync_repos.py [--repo key|--all] [--ref <sha-or-tag>] [--apply] [--workspace repos]`: renders into the clone; managed whole files are `.github/workflows/lw-pr-check.yml`, `.github/workflows/lw-secret-scan.yml`, `.github/workflows/lw-close-on-merge.yml` (on `pull_request: closed` into `{{integration_branch}}` when merged and the integration branch is not the default branch: runs leapwell `close_on_merge.py` which parses local `close|fix|resolve #N` refs from the PR body — pure `local_refs(body) -> list[int]`, cross-repo refs excluded — and closes them via `gh issue close` with `issues: write`), `.github/pull_request_template.md`, `.github/CODEOWNERS` (only if absent — otherwise report and leave); marked sections (`<!-- leapwell:begin -->…<!-- leapwell:end -->` for md, `# leapwell:begin`…`# leapwell:end` for yml) in `CLAUDE.md` and `.github/ISSUE_TEMPLATE/config.yml`. Dry-run prints unified diffs; `--apply` creates/uses local branch `chore/leapwell-sync`, writes, commits; refuses on dirty clone; never pushes. `--ref` default = `main`.
- Tests (temp git repos): first run diff/commit, second run no-op, marked section replace leaves other bytes identical, existing CODEOWNERS untouched, dirty clone refused, dry-run writes nothing.
- Commit `feat(sync): thin per-repo layer and sync script`.

### Task 7: Docs, wiki seed, mockups, CLAUDE.md, README

**Files:** `CLAUDE.md`, `README.md`, `docs/process/{SDLC,TICKETS,REQUIREMENTS,ADMIN_SETUP,REPOS}.md`, `wiki/{Home,Project-Overview,Repos-and-Areas,Glossary}.md`, `wiki/Feature-*.md` (7 feature pages from spec §4), `mockups/README.md`, `mockups/_template/README.md`, test `test_docs.py`.

- Port S `docs/process/SDLC.md` + `TICKETS.md` + `CLAUDE_ADMIN_SETUP.md` (→ ADMIN_SETUP.md with the rollout from spec §9), rewritten for the two-level ticket model and multi-repo; `REQUIREMENTS.md` = Discussions → promote → task → route → sub-issues → close-parents, with Wiki/mockup rules; `REPOS.md` generated-by-hand table that the test checks against repos.json.
- `CLAUDE.md`: workspace map (repos/), "start Claude from the leapwell root", human-only gates, ticket rules, skills/agents index, Engineering Design Standards (copied verbatim from `/Users/amresh/labs/UHIS/leapfrog-setup/CLAUDE.md` section of that name — leapwell is their home for LeapWell code).
- Wiki pages: short, factual, sourced from existing repo READMEs/CLAUDE.md files in P and the app; no patient names; each feature page links its repo(s) and the mockups folder.
- Tests: every skill and agent is listed in CLAUDE.md; REPOS.md table matches repos.json; docs mention no Jira keys as live process; `find_sensitive` clean over docs/wiki/mockups.
- Commit `docs: process, wiki seed, mockups, CLAUDE.md`.

### Task 8: Slim uhis_lf_mobile PR #744 (repo S, branch chore/sdlc-ticketing)

- Remove `.github/ISSUE_TEMPLATE/{bug,feature,task,release}.yml`, `.github/workflows/issue-check.yml`, `.claude/skills/lw-ticket/`, `docs/process/TICKETS.md`, `scripts/github/package_skill.sh` and ticket-only label/issue sections in `docs/process/CLAUDE_ADMIN_SETUP.md`; `config.yml` → blank issues enabled + contact link "File bugs, features and tasks in leapwell" → `https://github.com/Medtronic-LABS/leapwell/issues/new/choose`.
- `patterns.ISSUE_REF_RE` accepts `Medtronic-LABS/leapwell#N` (same regex as Task 1 — copy the pattern; this repo's copy is temporary until the toolkit is removed).
- `CLAUDE.md` "Process & ticketing" + `SDLC.md` + `JIRA_RETIREMENT.md`: tickets live in leapwell, route to sub-issues here, start Claude from the leapwell workspace.
- Update/remove the S tests that covered removed files; `python3 -m unittest discover -s scripts/sdlc/tests -t .` passes.
- Commit `refactor(process): move ticket filing to leapwell`; push `chore/sdlc-ticketing`; update PR #744 body.
