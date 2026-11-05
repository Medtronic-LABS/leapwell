# Local Frappe bench

A Docker Compose bench (MariaDB, three Redis, nginx proxy, backend container) for the Frappe code repos.
Ported from the UHIS-Next dev setup, with one difference: the app source is not scaffolded or kept inside the
bench tree. It is the workspace clone:

| App (bench name) | Workspace clone | Mounted at |
|---|---|---|
| `spice_next_core` | `repos/frappe_spice_next_core` | `/workspace-apps/spice_next_core` |
| `shukhee_integration` | `repos/leapwell_shukhee_integration` | `/workspace-apps/shukhee_integration` |

The setup script links each mount into `frappe-bench/apps/`, runs `pip install -e` and `install-app`, so edits
in `repos/<name>` show up in the bench immediately. (The mounts sit outside the bench tree because `bench init`
refuses to run when `frappe-bench/` already exists.) `frappe_theme` (required by `spice_next_core`) is fetched
with `bench get-app`.

## Use

```bash
cd env/frappe
cp .env.example .env            # first time; then change the passwords
bash frappe_setup.sh            # full setup (10-15 min first run, idempotent)
bash frappe_setup.sh --status   # containers, HTTP, MariaDB ping, backend log tail
bash frappe_setup.sh --stop     # docker compose down (data kept)
bash frappe_setup.sh --start    # up again + bench dev server
bash frappe_setup.sh --restart
bash frappe_setup.sh --help     # works without Docker
```

Prerequisites: Docker Desktop (compose v2) and the two clones (`/lw-setup` from the leapwell root).
The script refuses to run without `.env`. `.env` is gitignored; `.env.example` holds local-only placeholders
(`DB_ROOT_PASSWORD`, `ADMIN_PASSWORD`, `SITE_NAME`, `FRAPPE_BRANCH`).

Site: `http://localhost:8081`, user `Administrator`, password `ADMIN_PASSWORD` from `.env`.

## Run a repo's checks in the bench

```bash
docker compose exec backend bash -c 'cd frappe-bench && bench --site "$SITE" run-tests --app spice_next_core'
```

Use the site from `.env` and the commands in `repos.json` (`verify.test`, `verify.lint`, `verify.build`).

## Data

`development/` (bench workspace, MariaDB data, and on macOS the case-sensitive APFS sparse image
`db.sparseimage` mounted at `development/db`) is gitignored. Delete it only to start from scratch.

## Notes

- LeapWell runs on Frappe **v16** (owner decision, 2026-11-05): `FRAPPE_BRANCH` defaults to `version-16`, and
  `leapwell_shukhee_integration` requires Python >= 3.14 (the backend image `docker/backend-v16` is Python 3.14 /
  Node 24). `spice_next_core`'s README still says v15 and should be updated there. `frappe_theme` (branch
  `development`) on v16 is not yet verified, so the first run may need fixes.
- AI narrative features need an OpenAI-compatible LLM endpoint (e.g. Ollama) configured in Spice Settings; this
  env does not provision one.
- Not included from the UHIS-Next setup: PostgreSQL, Ollama, LiveKit, the second evaluation site, and the
  `leapwell_telemetry` / `uhis` scaffolds. Add them when a LeapWell repo needs them.
