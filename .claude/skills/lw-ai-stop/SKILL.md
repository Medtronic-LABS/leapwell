---
name: lw-ai-stop
description: Stop the AI Scribe service containers started from the leapfrog-ai-service clone (repos/leapfrog-ai-service). Keeps the database volume unless the user explicitly asks to remove it.
disable-model-invocation: true
---

# Stop the AI Scribe service

In `repos/leapfrog-ai-service` run `docker compose down` (stops the API, worker, PostgreSQL and Redis; named volumes with the database, logs and local audio are kept). Confirm with `docker compose ps` (empty).

`docker compose down -v` also deletes those volumes (jobs, notes, stored audio). Run it only if the user explicitly asks for a reset, and say what will be lost first.
