---
name: lw-frappe-start
description: Start the local Frappe bench in env/frappe (containers from a previous setup) and its dev server; --restart stops then starts.
argument-hint: "[--restart]"
disable-model-invocation: true
---

# Start the local Frappe bench

Run from the leapwell root. Needs a previous `/lw-frappe-setup` (the `env/frappe/development/` data exists) and `env/frappe/.env`; if either is missing, say so and point to `/lw-frappe-setup`. Never print `.env` values.

- Normal: `bash env/frappe/frappe_setup.sh --start`
- If `$ARGUMENTS` contains `--restart`: `bash env/frappe/frappe_setup.sh --restart`

The script attaches the APFS sparse image on macOS, brings the containers up, waits for MariaDB, restarts the bench dev server, socket.io and worker, and waits for `http://localhost:8081`. Show failures verbatim. Then run `/lw-frappe-status` and report the URL and that the credentials and site name are in `env/frappe/.env`.
