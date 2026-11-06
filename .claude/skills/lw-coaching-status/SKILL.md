---
name: lw-coaching-status
description: Health check of the local micro-coaching backend (repos/spice-coaching) and dashboard dev server - container states, readiness endpoints, dashboard URL. Read-only.
---

# Micro-coaching status

1. **Backend**, in `repos/spice-coaching` (missing clone: `/lw-setup --only coaching`): `docker compose ps`, then the README's readiness checks `curl -fsS http://localhost:8000/medtronics-api/ready` and `curl -fsS http://localhost:8001/health`. On failure show `docker compose logs --tail 40 <service>` for the failing service (redact tokens and personal data) and point to the repo's `docs/troubleshooting/README.md`.
2. **Dashboard** (`repos/spice-coaching-dashboard-ui`): the Vite dev server normally listens on `http://localhost:3000` (README); check with `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000`. A different port means Vite picked one - look at the dev server output.
3. **Android SDK** (`repos/spice-coaching-android`) has no service; see `/lw-coaching-android-build`.

Report a table (platform-api, ai-runtime, worker, beat, dashboard) with ok / not ok; suggest `/lw-coaching-start` for anything down. Never print `.env` values.
