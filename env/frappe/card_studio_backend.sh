#!/usr/bin/env bash
# Card Studio training backend for the local bench. It runs on the host, not in the bench, because it needs
# PyTorch and the repos/card-studio trainer. The bench reaches it at http://host.docker.internal:<port>.
#
# Usage: bash card_studio_backend.sh          (stays in the foreground; Ctrl+C stops it)
#
# Needs: the clones repos/frappe_card_studio and repos/card-studio, a Python environment with the trainer's
# packages at repos/.venvs/card-studio, and a token file next to it (repos/.venvs/card-studio/backend.token,
# one line, kept out of git). The same token goes into OCR Settings on the site.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS="$SCRIPT_DIR/../../repos"
VENV="$REPOS/.venvs/card-studio"
TOKEN_FILE="$VENV/backend.token"
PORT="${OCR_BACKEND_PORT:-8790}"

error() { echo "[x] $*" >&2; exit 1; }

[[ -d "$REPOS/frappe_card_studio" ]] || error "repos/frappe_card_studio is missing. Run /lw-setup --only card-studio-frappe."
[[ -f "$REPOS/card-studio/studio/trainer.py" ]] || error "repos/card-studio is missing. Run /lw-setup --only card-studio."
[[ -x "$VENV/bin/python" ]] || error "No Python environment at repos/.venvs/card-studio (see env/frappe/README.md)."
[[ -s "$TOKEN_FILE" ]] || error "No token at repos/.venvs/card-studio/backend.token (see env/frappe/README.md)."

OCR_BACKEND_TOKEN="$(<"$TOKEN_FILE")"
export OCR_BACKEND_TOKEN
export STUDIO_DIR="$REPOS/card-studio/studio"
export OCR_BACKEND_DATA="$VENV/backend-data"

cd "$REPOS/frappe_card_studio"
# Listens on 127.0.0.1 only; Docker Desktop forwards host.docker.internal to it.
exec "$VENV/bin/python" -m card_studio.card_studio.backend.server --port "$PORT"
