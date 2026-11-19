---
name: lw-frappe-stop
description: Stop the local Frappe bench containers in env/frappe. The bench and the database are kept.
disable-model-invocation: true
---

# Stop the local Frappe bench

From the leapwell root: `bash env/frappe/frappe_setup.sh --stop` (runs `docker compose down`; the bench under `env/frappe/development/` and the PostgreSQL Docker volume are preserved).

Confirm with `(cd env/frappe && docker compose ps)`; the list should be empty. Never delete `env/frappe/development/` or the database volume (no `docker compose down -v`) unless the user explicitly asks to start from scratch.
