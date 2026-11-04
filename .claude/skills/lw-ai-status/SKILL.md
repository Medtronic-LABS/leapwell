---
name: lw-ai-status
description: Health check of the local AI Scribe service in repos/leapfrog-ai-service - container states, /health on port 8095, recent API and worker logs. Read-only.
---

# AI Scribe status

In `repos/leapfrog-ai-service` (if it is missing, point to `/lw-setup --only ai`):

1. `docker compose ps` - expect `scribe-api`, `scribe-worker`, `scribe-postgres`, `scribe-redis` running, the API and database healthy.
2. `curl -fsS http://localhost:8095/health` - the service answers with an ok status and needs no auth.
3. On any failure show `docker compose logs --tail 40 api` and, for job problems, `docker compose logs --tail 40 worker`. Redact anything that looks like a token, key or patient detail before quoting logs.

Report a table (API, worker, PostgreSQL, Redis, /health) with ok / not ok, and suggest `/lw-ai-start` if the stack is down. Never print `.env` values.
