# Requirements flow

How a requirement travels from a first idea to code, and where each piece of knowledge lives. The
process rules (sizes, branching, PRs, release) are in [SDLC.md](SDLC.md); this file covers the front half.

| What | Lives in | Edited by |
|---|---|---|
| Ideas, field feedback, partner requests, questions | GitHub Discussions | anyone |
| Agreed requirements, bugs, tasks, releases | leapwell Issues (Project #4) | anyone via `lw-ticket` / `lw-promote` |
| How to build it | code-repo sub-issues | developers via `lw-route` |
| What the product is and does | GitHub Wiki (seeded from `wiki/`) | PM and developers via `lw-wiki` |
| What it should look like | `mockups/<feature-slug>/` in this repo | anyone, by PR |
| How we work | `docs/process/` in this repo | anyone, by PR |

## 1. Discussions: ideas

Categories: *Ideas*, *Field feedback*, *Partner requests*, *Q&A*, *Announcements*. The first three have forms
(`.github/DISCUSSION_TEMPLATE/`). Keep it short and free of patient data, partner-confidential details and
real names; this is public. Discuss, refine, link mockups. Nothing is built from a Discussion directly.

## 2. Promote: Discussion to leapwell item

When an idea is agreed, the PM runs `/lw-promote <discussion#>`. Claude reads the discussion, runs the
`lw-ticket` feature interview for what is missing (user, problem, acceptance criteria, programme, offline
behaviour, privacy), privacy-scrubs, shows a preview and, on an explicit "yes", creates the feature issue in
leapwell with a link back, then comments on the discussion with the issue link.

Bugs, tasks and releases skip Discussions and go straight to `/lw-ticket` (see [TICKETS.md](TICKETS.md)).

## 3. Triage

Twice a week the lead and PM set priority (`prio:*`), size and owner and move the item
Triage → Backlog → Ready. Only humans set priority. Items missing required sections carry `status:needs-info`.

## 4. Route: leapwell item to sub-issues

A developer runs `/lw-route <N>`. Claude reads the item, proposes one sub-issue per affected repo from
`repos.json` (title, body with repro or acceptance criteria and `Parent: Medtronic-LABS/leapwell#N`), and on
"yes" creates them in the code repos and links them as GitHub sub-issues. The item gets `status:routed` once
the developer confirms routing is complete. Work then follows [SDLC.md](SDLC.md): `/lw-start`, `/lw-fix` or
`/lw-feature`, `/lw-pr`.

## 5. Close: sub-issues to parent

- A merged PR closes its sub-issue (`Closes #n`; for non-default integration branches the
  `lw-close-on-merge` workflow in the code repo does it).
- The hourly `close-parents` workflow in leapwell (`scripts/sdlc/close_parents.py`) closes a `status:routed`
  item when it has at least one sub-issue and all are closed (including "not planned"), with a comment listing them.
  A sub-issue it cannot read blocks the close (fail safe).
- Items never routed are closed by hand or by a leapwell PR.

## Wiki rules

- The Wiki describes the project and its features: Home, Project overview, Repos & areas, one page per feature
  area, Glossary. Each feature page says what it is, who uses it, which repos hold the code, links the
  mockups, and lists open questions as links to Discussions.
- The seed lives in `wiki/` in this repo and was published once with `scripts/github/publish_wiki.sh`. After that
  the **GitHub Wiki is the live copy**; edit with `/lw-wiki <page>` (clone, edit, privacy scan, diff, push only on "yes")
  or in the Wiki UI. Keep `wiki/` as a seed, not a mirror.
- Facts only, no patient data, real names, hostnames, credentials or environment values. Link to code repos
  instead of copying code. Process rules stay in `docs/process/`; the Wiki links to them.
- Wiki page links use GitHub Wiki page names (no `.md`).

## Mockup rules

- Folder `mockups/<feature-slug>/` with a `README.md` linking its leapwell issue; copy `mockups/_template/`.
  Allowed formats: HTML, PNG, SVG, PDF. Added by PR, reviewed like code.
- **Fake data only.** The `mockup-scan` CI job runs the patient-data and secret patterns over mockup and wiki
  text files and fails the PR on a match. Details: [`mockups/README.md`](../../mockups/README.md).
- A mockup is a proposal. The agreed behaviour is the acceptance criteria on the leapwell item.
