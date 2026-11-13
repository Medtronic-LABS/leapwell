---
name: lw-ai-start
description: Start the AI Scribe service stack (API, worker, PostgreSQL, Redis) from repos/leapfrog-ai-service with docker compose and wait for its /health check.
disable-model-invocation: true
---

# Start the AI Scribe service

Run from the leapwell root. The service is the private repo `leapfrog-ai-service`; if `repos/leapfrog-ai-service` is missing, run `/lw-setup --only ai` (needs repo access; ask the team lead if the clone fails).

1. **Env.** `repos/leapfrog-ai-service/.env` must exist. If not, `cp repos/leapfrog-ai-service/env.example repos/leapfrog-ai-service/.env` and tell the user to fill in the provider keys and settings they were given (AI provider keys, storage settings; `DEV_SKIP_AUTH=true` is for local dev only). Never print or echo `.env` values and never copy them elsewhere. Do not start the stack until the user confirms the file is filled in.

2. **Start.** In `repos/leapfrog-ai-service`: `docker compose up -d` (builds the image on the first run). This starts `scribe-api` on port 8095, `scribe-worker`, PostgreSQL 16 (host port `DB_HOST_PORT`, default 5432) and Redis (6379). If a host port is already taken (e.g. a native PostgreSQL), set `DB_HOST_PORT` in `.env` instead of stopping the other service.

3. **Wait and verify.** `docker compose ps` in the same directory, then poll `curl -fsS http://localhost:8095/health` until it answers (the API healthcheck allows about 40 seconds of start-up). On failure show `docker compose logs --tail 60 api`.

4. **Report** the container states and the health result. Useful URLs: `http://localhost:8095/health`, Swagger at `http://localhost:8095/docs`. Point the mobile app at it through the AI service URL key in its `env.development.json` (never print that file).

Stop with `/lw-ai-stop`; run its tests with `/lw-ai-test`.
