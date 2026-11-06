---
name: lw-coaching-stop
description: Stop the local micro-coaching backend containers (repos/spice-coaching) and the coaching dashboard dev server started by lw-coaching-start.
argument-hint: "[backend|dashboard|all]"
disable-model-invocation: true
---

# Stop micro-coaching

`$ARGUMENTS`: `backend`, `dashboard` or `all` (default `all`).

- **Backend:** in `repos/spice-coaching` run `docker compose down` (the inverse of the documented `docker compose up --build`; add `--profile docs-static` if it was started with that profile). Database volumes are kept. `docker compose down -v` deletes them - only on explicit request, after saying what is lost. Confirm with `docker compose ps`.
- **Dashboard:** stop the `npm run dev` process that `/lw-coaching-start` launched (stop that background task; if it was started elsewhere, tell the user to press Ctrl-C in that terminal). Do not kill unrelated Node processes.

Report what was stopped and what is still running.
