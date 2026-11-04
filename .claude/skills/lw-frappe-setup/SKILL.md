---
name: lw-frappe-setup
description: First-time (or repair) setup of the local Frappe bench in env/frappe - Docker containers, bench init, and the frappe_spice_next_core and leapwell_shukhee_integration apps from the workspace clones, site, migrate, dev server. Idempotent.
disable-model-invocation: true
---

# Set up the local Frappe bench

Run from the leapwell root. Details: `env/frappe/README.md`. The Frappe repos' `verify` commands in `repos.json` (`core`, `shukhee`) run inside this bench.

1. **Preconditions** (stop with the fix if any fails):
   - Docker Desktop running (`docker info`).
   - `repos/frappe_spice_next_core` and `repos/leapwell_shukhee_integration` exist -> else `/lw-setup --only core,shukhee`.
   - `env/frappe/.env` exists -> else tell the user: `cp env/frappe/.env.example env/frappe/.env` and change the passwords. The script refuses to run without it. Never print `.env` or put its values into commands or reports.

2. **Run** `bash env/frappe/frappe_setup.sh` (about 10-15 minutes the first time; safe to re-run). It:
   1. creates/attaches the case-sensitive APFS sparse image for MariaDB on macOS (under `env/frappe/development/`, gitignored),
   2. builds the backend image and starts MariaDB, three Redis, nginx and the backend,
   3. runs `bench init` for the `FRAPPE_BRANCH` in `.env`,
   4. links the two workspace clones into `apps/`, `pip install -e` each,
   5. fetches `frappe_theme` (needed by `spice_next_core`),
   6. creates the site named in `.env`, installs the three apps, enables developer mode, runs `migrate`,
   7. starts the bench dev server, socket.io and a background worker.
   Show the script output verbatim on failure; do not retry blindly. A failed `bench init` leaves a partial `env/frappe/development/workspace/frappe-bench`; ask before deleting anything under `development/`.

3. **Verify** with `/lw-frappe-status` and report: the URL `http://localhost:8081`, user `Administrator`, and that the password and site name are in `env/frappe/.env`.

Never run this against shared, training or production servers; it is local only.
