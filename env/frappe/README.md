# Local Frappe bench

A Docker Compose bench (PostgreSQL 16, three Redis, nginx proxy, backend container) for the Frappe code repos.
Ported from the UHIS-Next dev setup, with two differences: the site runs on PostgreSQL, and the app source is not scaffolded or kept inside the
bench tree. It is the workspace clone:

| App (bench name) | Workspace clone | Mounted at |
|---|---|---|
| `spice_next_core` | `repos/frappe_spice_next_core` | `/workspace-apps/spice_next_core` |
| `shukhee_integration` | `repos/leapwell_shukhee_integration` | `/workspace-apps/shukhee_integration` |
| `leapwell_telemetry` | `repos/frappe_leapwell_telemetry` | `/workspace-apps/leapwell_telemetry` |
| `uhis` | `repos/frappe_uhis` | `/workspace-apps/uhis` |
| `card_studio` | `repos/frappe_card_studio` | `/workspace-apps/card_studio` |

The setup script links each mount into `frappe-bench/apps/`, runs `pip install -e` and `install-app`, so edits
in `repos/<name>` show up in the bench immediately. (The mounts sit outside the bench tree because `bench init`
refuses to run when `frappe-bench/` already exists.) `frappe_theme` (required by `spice_next_core`) is fetched
with `bench get-app`.

## Use

```bash
cd env/frappe
cp .env.example .env            # first time; then change the passwords
bash frappe_setup.sh            # full setup (10-15 min first run, idempotent)
bash frappe_setup.sh --status   # containers, HTTP, PostgreSQL check, backend log tail
bash frappe_setup.sh --stop     # docker compose down (data kept)
bash frappe_setup.sh --start    # up again + bench dev server
bash frappe_setup.sh --restart
bash frappe_setup.sh --help     # works without Docker
```

Prerequisites: Docker Desktop (compose v2) and the five clones (`/lw-setup` from the leapwell root).
The script refuses to run without `.env`. `.env` is gitignored; `.env.example` holds local-only placeholders
(`DB_ROOT_PASSWORD`, `ADMIN_PASSWORD`, `SITE_NAME`, `FRAPPE_BRANCH`).

Site: `http://localhost:8082` (the port is `FRAPPE_HTTP_PORT` in `.env`), user `Administrator`, password `ADMIN_PASSWORD` from `.env`.

## Run a repo's checks in the bench

```bash
docker compose exec backend bash -c 'cd frappe-bench && bench --site "$SITE" run-tests --app spice_next_core'
```

Use the site from `.env` and the commands in `repos.json` (`verify.test`, `verify.lint`, `verify.build`).

## Card Studio training

One-time, from the leapwell root (needs `uv`; Python 3.12 is the version this was set up and tested with):

```bash
uv venv --python 3.12 repos/.venvs/card-studio
uv pip install --python repos/.venvs/card-studio/bin/python -r repos/card-studio/requirements.txt \
    torch "opencv-python>=4.13,<5" onnx onnxscript requests pyyaml pillow-heif
(umask 077; python3 -c "import secrets; print(secrets.token_urlsafe(40))" > repos/.venvs/card-studio/backend.token)
```

Then start the backend (foreground; Ctrl+C stops it):

```bash
bash env/frappe/card_studio_backend.sh
```

In **OCR Settings** on the site set the backend URL to `http://host.docker.internal:8790` and the token to the
content of `repos/.venvs/card-studio/backend.token`. The backend listens on 127.0.0.1 only; keep it that way,
because it accepts training data. `repos/` is gitignored, so the token and the environment stay out of git.

## Data

The bench lives in `development/workspace` (gitignored) and the database in the Docker volume `db-data`.
To start from scratch remove both: `docker compose down -v`, then delete `development/`.

## Notes

- LeapWell runs on Frappe **v16** (owner decision, 2026-11-05): `FRAPPE_BRANCH` defaults to the release tag `v16.60.2` (set it to `version-16` to follow the branch tip), and
  `leapwell_shukhee_integration` requires Python >= 3.14 (the backend image `docker/backend-v16` is Python 3.14 /
  Node 24). `spice_next_core`'s README still says v15 and should be updated there. `frappe_theme` (branch
  `development`) on v16 is not yet verified, so the first run may need fixes.
- `card_studio` works for cards, scans, labeling and reading as installed. Training needs its backend, which
  runs on the host (it needs PyTorch and the `repos/card-studio` trainer): see "Card Studio training" below.
- AI narrative features need an OpenAI-compatible LLM endpoint (e.g. Ollama) configured in Spice Settings; this
  env does not provision one.
- The backend image installs the PostgreSQL 16 client so `bench backup` matches the server; keep
  `POSTGRES_MAJOR` in the Dockerfile and the `db` image in `docker-compose.yml` on the same major version.
- Not included from the UHIS-Next setup: MariaDB, Ollama, LiveKit and the second evaluation site. Add them
  when a LeapWell repo needs them.
