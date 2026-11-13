---
name: lw-coaching-start
description: Start the micro-coaching backend (repos/spice-coaching, docker compose) and/or the coaching dashboard dev server (repos/spice-coaching-dashboard-ui), using each repo's documented commands.
argument-hint: "[backend|dashboard|all]"
disable-model-invocation: true
---

# Start micro-coaching

`$ARGUMENTS`: `backend`, `dashboard` or `all` (default `all`). Run from the leapwell root. Repos: `spice-coaching` (key `coaching`), `spice-coaching-dashboard-ui` (key `coaching-dashboard`); integration branch `leapwell-main`. Missing clone: `/lw-setup --only coaching,coaching-dashboard`. Only the commands below are taken from the repos' READMEs; for anything else (env variables, seed data, credentials) read the repo README and ask the user rather than guessing. Never print `.env` content.

## Backend (`repos/spice-coaching`)

A `uv` workspace: `platform-api` (public API), `platform-worker`, `platform-celery-beat`, private `ai-runtime`, one-shot `migrate`, with PostgreSQL, Redis and ClickHouse in the compose file.

1. First run: `uv sync --locked --all-packages --group dev`. (The README also lists `uv run pre-commit install`; skip it here - leapwell points the clone's git hooks at its own `.githooks`.) Required environment/config for the stack is described in the repo README; confirm it is in place before starting.
2. `docker compose up --build` in `repos/spice-coaching` (add `-d` to keep your terminal; add `--profile docs-static` to also serve the docs on port 18081).
3. Expect `migrate` and `clickhouse-init` to exit 0, and `db`, `redis`, `clickhouse`, `ai-runtime`, `platform-api`, `platform-celery-worker`, `platform-celery-beat` running: `docker compose ps`.
4. Readiness: `curl -fsS http://localhost:8000/medtronics-api/ready` and `curl -fsS http://localhost:8001/health`. On failure: the repo's `docs/troubleshooting/README.md`.

## Dashboard (`repos/spice-coaching-dashboard-ui`)

1. `npm install`; first time `cp .env.example .env` and set `VITE_API_BASE_URL` (the backend origin plus API root path, see the README) and related URLs - the values come from the team or the local backend above.
2. `npm run dev` (long-running; run in the background and keep its output file). Vite prints the URL, typically `http://localhost:3000`.
3. Access needs a user with the coaching suite access; see the README "Access" section.

Report what is running with URLs. Stop with `/lw-coaching-stop`, check with `/lw-coaching-status`.
