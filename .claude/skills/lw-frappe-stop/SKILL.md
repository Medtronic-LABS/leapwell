---
name: lw-frappe-stop
description: Stop the local Frappe bench containers in env/frappe. Data under env/frappe/development is kept.
disable-model-invocation: true
---

# Stop the local Frappe bench

From the leapwell root: `bash env/frappe/frappe_setup.sh --stop` (runs `docker compose down`; the bench, database and sparse image under `env/frappe/development/` are preserved).

Confirm with `(cd env/frappe && docker compose ps)`; the list should be empty. Never delete `env/frappe/development/` or detach the sparse image unless the user explicitly asks to start from scratch.
