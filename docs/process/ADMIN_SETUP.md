# Admin setup: rollout of the leapwell hub

One-time steps that make the process in [SDLC.md](SDLC.md) work for everyone. Nothing here was run by the
build that created this repo: GitHub settings, the Wiki, Discussion categories and Claude org settings are
changed only by people. Every script below is **dry-run by default**: read the output, then re-run with `--apply`.

| Who | Section |
|---|---|
| Repo owner / org owner of `Medtronic-LABS` | 1 to 5, 7, 8 |
| Claude org **Owner** (Team / Enterprise plan) | 6 |
| Every developer | 9 |

## 1. Rollout order

1. Seed `main` with the README and `.gitignore`; everything else arrives on `chore/leapwell-hub` as a draft
   pull request. The owner reviews and merges it.
2. On the merged repo run, each first as a dry-run: `scripts/github/sync_labels.sh`,
   `scripts/github/setup_discussions.sh`, `scripts/github/setup_project.sh`, `scripts/github/publish_wiki.sh`,
   `scripts/github/protect_branches.sh` (details below). Upload the `lw-ticket` org skill (section 6).
3. `python3 scripts/sync/sync_repos.py --repo <key>` per code repo (after `/lw-setup`), review the diff, then
   `--apply`; it commits on a local `chore/leapwell-sync` branch inside `repos/<name>` and never pushes. The owner
   pushes each branch and opens the PR. Start with one repo and check that its `lw-pr-check`, `lw-secret-scan` and `lw-close-on-merge` run.
4. Announce to PM and QA: file everything in leapwell ([TICKETS.md](TICKETS.md)).

## 2. Labels, project fields and branch protection

Needs `gh` signed in as a repo admin (`gh auth refresh -s project` for the project script).

```sh
bash scripts/github/sync_labels.sh --all-repos       # dry-run: labels from .github/labels.yml, also in the code repos
bash scripts/github/sync_labels.sh --all-repos --apply
bash scripts/github/setup_project.sh                 # links leapwell to Project #4; Priority and Type fields
bash scripts/github/setup_project.sh --apply
bash scripts/github/protect_branches.sh              # leapwell main: 1 approval, CODEOWNERS, required checks
bash scripts/github/protect_branches.sh --apply
```

Required checks on leapwell `main`: `pr-check`, `sdlc-scripts`, `secret-scan`, `mockup-scan`. They appear in the
branch-protection picker only after they have run once; the script sets them by name through the API anyway.
Until the workflows are on `main` and have run, PRs wait on those checks. Code repos are protected by their own owners.

`setup_project.sh` never edits **Status** (the API replaces the whole option list and can wipe item values). In the
UI: Project → Settings → Status → add `Triage` at the top and `QA` between `In review` and `Done`. Target order:
Triage, Backlog, Ready, In progress, In review, QA, Done.

## 3. Project #4 built-in workflows

Project → Workflows (UI only), enable:

| Workflow | Setting |
|---|---|
| Auto-add to project | filter `repo:Medtronic-LABS/leapwell is:issue`; add one more Auto-add workflow per code repo to show sub-issues (the Repository field separates the two levels) |
| Item added to project | set Status = Triage |
| Item closed | set Status = Done |
| Pull request merged | set Status = Done |
| Item reopened | set Status = In progress |

## 4. Discussions

`bash scripts/github/setup_discussions.sh [--apply]` enables Discussions and reports which categories exist.
Categories cannot be created through the API; in the UI (repo → Discussions → pencil icon next to Categories) add:

| Category | Format |
|---|---|
| Ideas | Open-ended discussion |
| Field feedback | Open-ended discussion |
| Partner requests | Open-ended discussion |
| Q&A | Question / Answer |
| Announcements | Announcement |

The forms in `.github/DISCUSSION_TEMPLATE/` (`ideas.yml`, `field-feedback.yml`, `partner-requests.yml`) are matched
by category slug, so keep those category names.

## 5. Wiki first page

GitHub creates the wiki's git remote only after a first page exists. In the UI: repo → Wiki → Create the first page
(any text). Then `bash scripts/github/publish_wiki.sh` (dry-run: clones, commits locally, never pushes) and
`--apply`. It refuses to overwrite a non-empty wiki unless `--force`. After seeding, the GitHub Wiki is the live
copy and `/lw-wiki <page>` edits it.

## 6. Claude org

### The `lw-ticket` skill (chat intake for PM/QA)

1. From a clean checkout of `main`: `bash scripts/github/package_skill.sh --apply`. It writes
   `dist/skills/lw-ticket.zip` (folder `lw-ticket/` at the zip root, matching the skill name; `dist/` is gitignored).
   It is the same skill Claude Code uses; never edit the zip.
2. Claude organisation settings → Skills → upload the zip as an org-wide skill. Per Anthropic's help article
   "Managing skills as an admin", Owners can add org-wide skills by uploading a `.zip` whose folder name matches
   the skill name; users can toggle it off but not delete it. Exact menu names may differ.
3. After any change to `.claude/skills/lw-ticket/`, re-package and upload again.

### GitHub connector

The chat skill creates issues through a GitHub connector: add GitHub's hosted MCP server as a **custom connector**
in the organisation's Connectors settings; each user then connects it with their own GitHub account so issues
are created under their name. **Not verified** for our org: the `Medtronic-LABS` org may need an owner to approve
the connector's OAuth app. Test with one user (file a test ticket, check it, close it). If it does not work,
`lw-ticket` falls back to showing the finished ticket as Markdown plus a prefilled issue-form link.

## 7. Secrets and access

- **`LEAPWELL_BOT_TOKEN`** (leapwell repo secret, used by `close-parents`): a fine-grained PAT or GitHub App token
  with **Issues: read** on all seven code repos (one, `leapfrog-ai-service`, is private) and **Issues: write** on
  leapwell. Without it the workflow falls back to `GITHUB_TOKEN`, which cannot read the private repo, so a routed
  item with a sub-issue there is never auto-closed (fail safe).
- Nothing else is needed as a secret. Never put env values, hash keys, tokens or passwords in the repo or in docs.
- **Who needs what:** *triage* access on leapwell for PM and QA who set labels; *write* on leapwell for developers
  and on each code repo they work in (sub-issues are created in those repos and cross-repo links need access to
  both); the lead and PM own CODEOWNERS paths.
- **Fork PR workflows (public repo):** Settings → Actions → General → Fork pull request workflows → enable
  "Require approval for all outside collaborators", so a fork PR cannot run workflows (or reach secrets) unreviewed.
- **Keep-alive:** GitHub disables scheduled workflows after 60 days without repo activity. If `close-parents`
  stops running, trigger it once (Actions → Close parents → Run workflow, or `workflow_dispatch`) to re-arm it.
- **Private vulnerability reporting:** repo Settings → Code security → enable it. The issue chooser, `lw-ticket`
  and `lw-security` send reports to the leapwell security advisory page; it works only once this is on.
- **First full-history secret scan:** CI scans only each PR's commits. Run `gitleaks git --redact` once over the
  full history and rotate anything found.

## 8. Open decisions (owner)

1. Bug fields (version, build, device) are required in the bug form; make them optional for non-mobile components.
2. `lw-mobile-release` needs a dev env file for the `dev` target (`env.staging.json` is assumed); confirm or name another.
3. The first Frappe v16 run of `env/frappe` is unverified (`frappe_theme` on v16, Python 3.14 image); expect fixes.
4. After leapwell is merged, remove the duplicated toolkit from `uhis_lf_mobile` (agents, workflow skills, guard hook,
   `scripts/sdlc`); it was left in place for now.
5. Mobile's own `pr-check` and `secret-scan` versus the thin `lw-pr-check` / `lw-secret-scan` layer: keep one of each per repo to avoid duplicate checks.
6. Whether Claude's Grep/Glob really search `repos/` through the shipped `.ignore` (`!/repos/`) is unverified.
7. Thin workflows check out leapwell at `main` until the owner creates a tag; then `sync_repos.py --ref <tag>` re-pins everywhere.
8. Integration branches in `repos.json` are starting values read on 2026-11-04; correct them there.

## 9. Every developer, once

See SDLC.md section 11: clone leapwell, `gh auth login`, `gh auth refresh -s project`, start `claude` from the leapwell
root, run `/lw-setup`. If you had a personal, untracked `.claude/settings.json`, rename it to
`.claude/settings.local.json` **before** pulling, otherwise git refuses to overwrite it. Personal permissions
belong in `settings.local.json` (gitignored).
