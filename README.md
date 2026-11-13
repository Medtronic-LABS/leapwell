# LeapWell

Home of the LeapWell product team (Apon Sushashthya community health app, AI Scribe, micro-coaching and the
Frappe backend): requirements, tickets, mockups, and the shared developer workspace and AI-assisted SDLC for
all LeapWell code repos.

This repository is **public**. Never post patient data, names, credentials or environment values anywhere in it.

## What goes where

| I want to... | Do this |
|---|---|
| Share an idea, field feedback or a partner request | Start a [Discussion](https://github.com/Medtronic-LABS/leapwell/discussions) |
| Report a bug, request a feature, file a task or release | Say "file a bug" to Claude, or `/lw-ticket`; or use the [issue forms](https://github.com/Medtronic-LABS/leapwell/issues/new/choose). Guide: [TICKETS.md](docs/process/TICKETS.md) |
| Learn what the product is and does | The GitHub Wiki (seeded from [`wiki/`](wiki/Home.md)) |
| Look at or add a mockup | [`mockups/`](mockups/README.md), added by pull request, fake data only |
| Understand how we work | [SDLC.md](docs/process/SDLC.md), [REQUIREMENTS.md](docs/process/REQUIREMENTS.md) |

## Developer quick start

```sh
git clone https://github.com/Medtronic-LABS/leapwell.git
cd leapwell
gh auth login && gh auth refresh -s project
claude            # start Claude from the leapwell root, always
```

The first time, Claude asks whether you trust this folder - accept it. Until you do, the read-only commands
pre-approved in `.claude/settings.json` are ignored and every `git status` asks for permission (the guard hook
runs either way).

Then, inside Claude, run `/lw-setup`. It clones the seven code repos listed in
[REPOS.md](docs/process/REPOS.md) into `repos/`, points their git hooks at leapwell's, and reports which tools
(git, gh, python3 3.11+, flutter, docker, node, java) are missing for which area. It is safe to re-run.

Typical flow: a developer picks a leapwell item, `/lw-route <N>` creates sub-issues in the affected repos,
`/lw-start <repo> <n>`, then `/lw-fix` (small) or `/lw-feature` (large), then `/lw-pr`. Claude proposes, a human
decides: merging, tagging, releasing, priorities and GitHub settings are never automatic. See
[CLAUDE.md](CLAUDE.md) for the skills and agents index.

Run the repo's own checks with `python3 -m unittest discover -s scripts -t .`.

## Docs

- [docs/process/SDLC.md](docs/process/SDLC.md): the process, sizes, gates, release, hotfix, agents
- [docs/process/TICKETS.md](docs/process/TICKETS.md): one-page filing guide for PM and QA
- [docs/process/BOARD.md](docs/process/BOARD.md): the project board: issue types, sprints, views, planning checklist
- [docs/process/REQUIREMENTS.md](docs/process/REQUIREMENTS.md): Discussions, promotion, routing, Wiki and mockup rules
- [docs/process/ADMIN_SETUP.md](docs/process/ADMIN_SETUP.md): owner rollout, secrets, open decisions
- [docs/process/REPOS.md](docs/process/REPOS.md): the seven repos, branches and verify commands
- [docs/superpowers/specs/2026-11-04-leapwell-hub-design.md](docs/superpowers/specs/2026-11-04-leapwell-hub-design.md): design record

## Rollout status

The hub is built on the `chore/leapwell-hub` branch and awaits owner review. Not done yet, and only the owner can
do them: merging, labels, Discussion categories, Project fields and workflows, the first Wiki page and publishing
the seed, branch protection, the `LEAPWELL_BOT_TOKEN` secret, the `lw-ticket` org skill upload, and syncing the
thin layer into each code repo. Steps and open decisions are in [ADMIN_SETUP.md](docs/process/ADMIN_SETUP.md).
