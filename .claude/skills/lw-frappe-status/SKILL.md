---
name: lw-frappe-status
description: Health check of the local Frappe bench in env/frappe - container states, HTTP on port 8081, MariaDB ping, recent backend logs. Read-only.
---

# Frappe bench status

From the leapwell root run `bash env/frappe/frappe_setup.sh --status`. It prints container states (`docker compose ps`), the HTTP status of `http://localhost:8081`, a MariaDB ping and the last 15 backend log lines. It needs `env/frappe/.env`; if that is missing say so and point to `/lw-frappe-setup`. Never print `.env` values.

Report a table of Containers, Web (8081), MariaDB, Backend log, each ok / not ok, with the failing detail. If the web check fails while containers are up, the dev server probably is not running: suggest `/lw-frappe-start`; to read its log: `(cd env/frappe && docker compose exec backend tail -30 /tmp/bench.log)`.
