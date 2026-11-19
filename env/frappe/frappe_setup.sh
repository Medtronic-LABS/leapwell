#!/usr/bin/env bash
# Local Frappe bench for the LeapWell Frappe apps (frappe_spice_next_core, leapwell_shukhee_integration,
# frappe_leapwell_telemetry, frappe_uhis, frappe_card_studio).
# The app source is the workspace clone under ../../repos, bind-mounted into the backend container.
#
# Usage: bash frappe_setup.sh [--start | --stop | --restart | --status | --help]
#   (no flag)  full idempotent setup, 10-15 min on a first run
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[*]${NC} $*"; }
success() { echo -e "${GREEN}[ok]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}${BLUE}== $* ==${NC}"; }

usage() {
  cat <<'USAGE'
Usage: bash frappe_setup.sh [--start | --stop | --restart | --status | --help]

  (no flag)   full idempotent setup: containers, bench init, apps, site, migrate, dev server
  --start     bring the containers up and start the bench dev server
  --stop      docker compose down (the bench under development/ and the database volume are kept)
  --restart   --stop, then --start
  --status    container states, HTTP check, PostgreSQL check, recent backend logs
  --help      this text

Needs a .env next to this script (cp .env.example .env) and the workspace clones of the five Frappe
apps under repos/ (run /lw-setup).
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BENCH_HOME="/home/frappe/frappe-bench"
# <bench app name>:<workspace clone under ../../repos>, in install order: shukhee and telemetry require
# spice_next_core, uhis requires all three.
WORKSPACE_APPS=(
  "spice_next_core:frappe_spice_next_core"
  "shukhee_integration:leapwell_shukhee_integration"
  "leapwell_telemetry:frappe_leapwell_telemetry"
  "uhis:frappe_uhis"
  "card_studio:frappe_card_studio"
)

DO_START=false; DO_STOP=false; DO_RESTART=false; DO_STATUS=false

for arg in "$@"; do
  case "$arg" in
    --start)    DO_START=true ;;
    --stop)     DO_STOP=true ;;
    --restart)  DO_RESTART=true ;;
    --status)   DO_STATUS=true ;;
    -h|--help)  usage; exit 0 ;;
    *) usage >&2; error "Unknown flag: $arg" ;;
  esac
done

check_docker() {
  command -v docker &>/dev/null || error "Docker not found. Install Docker Desktop and try again."
  docker compose version &>/dev/null || error "'docker compose' (v2) not available. Update Docker Desktop."
  docker info &>/dev/null || error "Docker daemon is not running. Start Docker Desktop and try again."
}

load_env() {
  [[ -f .env ]] || error "env/frappe/.env is missing. Run: cp .env.example .env  (then change the passwords)."
  # shellcheck disable=SC1091
  set -a; source .env; set +a
  : "${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is not set in env/frappe/.env}"
  : "${ADMIN_PASSWORD:?ADMIN_PASSWORD is not set in env/frappe/.env}"
  : "${SITE_NAME:?SITE_NAME is not set in env/frappe/.env}"
  FRAPPE_BRANCH="${FRAPPE_BRANCH:-v16.60.2}"
  # Host port of the site; the same default is in docker-compose.yml.
  export FRAPPE_HTTP_PORT="${FRAPPE_HTTP_PORT:-8082}"
  SITE_URL="http://localhost:$FRAPPE_HTTP_PORT"
}

check_workspace_apps() {
  local entry clone
  for entry in "${WORKSPACE_APPS[@]}"; do
    clone="${entry#*:}"
    [[ -d "../../repos/$clone" ]] || error "repos/$clone is missing. Run /lw-setup (or: bash scripts/workspace/setup.sh --only core,shukhee,telemetry,uhis,card-studio-frappe) from the leapwell root."
  done
}

prepare_workspace() {
  mkdir -p development/workspace
}

db_ready() {
  docker compose exec -T db pg_isready -U postgres -q 2>/dev/null
}

wait_for_db() {
  info "Waiting for PostgreSQL to be ready..."
  local retries=20
  until db_ready; do
    ((retries--)) || error "PostgreSQL did not become healthy in time."
    sleep 3
  done
  success "PostgreSQL is ready."
}

bench_init_done() {
  docker compose exec -T backend test -f "$BENCH_HOME/Procfile" 2>/dev/null
}

site_exists() {
  docker compose exec -T backend test -f "$BENCH_HOME/sites/$SITE_NAME/site_config.json" 2>/dev/null
}

app_installed() {
  local app="$1"
  docker compose exec -T backend bash -c \
    "export PATH=\$PATH:/home/frappe/.local/bin; cd $BENCH_HOME && bench --site '$SITE_NAME' list-apps 2>/dev/null | grep -q '^${app}\b'"
}

bench_exec() {
  docker compose exec -T backend bash -c "export PATH=\$PATH:/home/frappe/.local/bin; cd $BENCH_HOME && $*"
}

wait_for_site() {
  info "Waiting for site at $SITE_URL (Frappe takes ~30 s to warm up)..."
  local retries=40
  until curl -sf -o /dev/null "$SITE_URL"; do
    ((retries--)) || { warn "Site did not respond - check: docker compose exec backend tail -30 /tmp/bench.log"; return; }
    sleep 5
  done
  success "Site is up at $SITE_URL"
}

start_bench_server() {
  docker compose exec -T backend bash -c \
    "pkill -9 -f '[b]ench serve|[b]ench_helper|[g]unicorn|[s]ocketio' 2>/dev/null; sleep 2; true"
  info "Starting bench dev server..."
  docker compose exec -d backend bash -c \
    "export PATH=\$PATH:/home/frappe/.local/bin; cd $BENCH_HOME && bench --site '$SITE_NAME' serve --port 8000 --noreload > /tmp/bench.log 2>&1"
  info "Starting socketio realtime server..."
  docker compose exec -d backend bash -c \
    "nohup node $BENCH_HOME/apps/frappe/socketio.js > /tmp/socketio.log 2>&1 &"
  info "Starting background worker..."
  docker compose exec -d backend bash -c \
    "export PATH=\$PATH:/home/frappe/.local/bin; cd $BENCH_HOME && bench worker --queue default,short,long >> /tmp/worker.log 2>&1"
}

print_summary() {
  echo ""
  echo -e "${BOLD}${GREEN}------------------------------------------${NC}"
  echo -e "${BOLD}  LeapWell Frappe bench is running${NC}"
  echo -e "${BOLD}${GREEN}------------------------------------------${NC}"
  echo -e "  URL      : $SITE_URL"
  echo -e "  User     : Administrator (password: ADMIN_PASSWORD in env/frappe/.env)"
  echo -e "  Site     : $SITE_NAME"
  echo ""
  echo -e "  Shell    : docker compose exec backend bash   (run from env/frappe)"
  echo ""
}

do_status() {
  step "Status"
  check_docker; load_env

  echo ""
  docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true

  echo ""
  info "Checking $SITE_URL ..."
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" 2>/dev/null || true)
  http_code="${http_code:-000}"
  if [[ "$http_code" == "200" || "$http_code" == "302" || "$http_code" == "301" ]]; then
    success "Web ($FRAPPE_HTTP_PORT): HTTP $http_code"
  else
    warn "Web ($FRAPPE_HTTP_PORT): HTTP $http_code - site may still be starting"
  fi

  info "Checking PostgreSQL ..."
  if db_ready; then
    success "PostgreSQL: healthy"
  else
    warn "PostgreSQL: not responding"
  fi

  info "Recent backend logs:"
  docker compose logs --tail 15 backend 2>/dev/null || true
}

do_stop() {
  step "Stopping"
  check_docker
  # compose interpolates .env; give it harmless defaults so a stop works even if .env was removed
  DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-unused-for-stop}" docker compose down
  success "All containers stopped (the bench under development/ and the database volume are kept)."
}

ensure_build_deps() {
  docker compose exec -T backend bash -c "
    git config --global --add safe.directory '*'
    # The backend image already has these (its Python is built from source, so there is no python3-dev package).
    command -v gcc git node yarn &>/dev/null && exit 0
    sudo apt-get update -qq
    sudo apt-get install -y python3-dev python3-pip gcc git nodejs npm -qq
    sudo npm install -g yarn --loglevel=error
  "
}

# Link a bind-mounted workspace clone into bench apps/, pip-install it editable, and register it in apps.txt.
link_workspace_app() {
  local app="$1"
  docker compose exec -T backend test -d "/workspace-apps/$app" \
    || error "/workspace-apps/$app is not mounted - check docker-compose.yml and that repos/ clones exist."
  bench_exec "ln -sfn /workspace-apps/$app apps/$app"
  if docker compose exec -T backend bash -c \
      "test -x $BENCH_HOME/env/bin/python && $BENCH_HOME/env/bin/python -c 'import $app' &>/dev/null"; then
    success "$app already pip-installed - skipping."
  else
    step "Pip-installing $app (editable, from the workspace clone)"
    bench_exec "./env/bin/python -m pip install -e apps/$app || uv pip install --python ./env/bin/python -e apps/$app"
    success "$app installed."
  fi
  register_app "$app" sites/apps.txt
  register_app "$app" apps.txt
}

# Add an app to one of the bench's app lists. bench rewrites these files without a final newline, so end the
# last line first; otherwise two names end up joined on one line.
register_app() {
  local app="$1" list="$2"
  bench_exec "touch '$list'; grep -qxF '$app' '$list' && exit 0; [[ -s '$list' && -n \"\$(tail -c1 '$list')\" ]] && echo >> '$list'; echo '$app' >> '$list'"
}

install_site_app() {
  local app="$1"
  if app_installed "$app"; then
    success "$app already installed on the site - skipping."
  else
    step "Installing $app on the site"
    bench_exec "bench --site '$SITE_NAME' install-app $app"
    success "$app installed."
  fi
}

do_start() {
  step "Starting"
  check_docker; load_env; check_workspace_apps
  prepare_workspace

  info "Bringing containers up..."
  docker compose up -d
  wait_for_db

  step "Ensuring system build dependencies"
  ensure_build_deps
  success "Build dependencies ready."

  start_bench_server
  wait_for_site
  print_summary
}

do_full_setup() {
  step "Pre-flight"
  check_docker; load_env; check_workspace_apps
  [[ -f docker-compose.yml ]] || error "docker-compose.yml not found next to the script."

  prepare_workspace

  step "Starting containers (builds the backend image on first run)"
  docker compose up -d --build
  wait_for_db

  step "Ensuring system build dependencies"
  ensure_build_deps
  success "Build dependencies ready."

  if bench_init_done; then
    success "bench already initialised - skipping."
  else
    step "Initialising bench $FRAPPE_BRANCH (5-10 min on first run)"
    docker compose exec -T backend bash -c \
      "export PATH=\$PATH:/home/frappe/.local/bin; bench init --frappe-branch '$FRAPPE_BRANCH' --python python3 --skip-redis-config-generation frappe-bench"

    docker compose exec -T backend bash -c "
      cat > $BENCH_HOME/sites/common_site_config.json <<CONF
{
  \"db_host\": \"db\",
  \"db_port\": 5432,
  \"redis_cache\": \"redis://redis-cache:6379\",
  \"redis_queue\": \"redis://redis-queue:6379\",
  \"redis_socketio\": \"redis://redis-socketio:6379\",
  \"socketio_port\": 9000,
  \"default_site\": \"$SITE_NAME\"
}
CONF
      sed -i '/^redis_/d' $BENCH_HOME/Procfile
    "
    success "bench initialised."
  fi

  # spice_next_core first: frappe_theme and shukhee_integration depend on it / are required by it.
  link_workspace_app spice_next_core

  if docker compose exec -T backend test -d "$BENCH_HOME/apps/frappe_theme"; then
    success "frappe_theme sources present - skipping get-app."
  else
    step "Fetching frappe_theme (Suvaidyam, branch: development) - required by spice_next_core"
    bench_exec "bench get-app frappe_theme --branch development https://github.com/Suvaidyam/frappe_theme.git"
    register_app frappe_theme apps.txt
    success "frappe_theme fetched."
  fi

  local entry
  for entry in "${WORKSPACE_APPS[@]:1}"; do
    link_workspace_app "${entry%%:*}"
  done

  if site_exists; then
    success "Site '$SITE_NAME' already exists - skipping."
  else
    step "Creating site: $SITE_NAME"
    bench_exec "bench new-site '$SITE_NAME' \
      --db-type postgres \
      --db-host db \
      --db-port 5432 \
      --db-root-username postgres \
      --db-root-password '$DB_ROOT_PASSWORD' \
      --admin-password '$ADMIN_PASSWORD'"
    success "Site created."
  fi

  install_site_app frappe_theme
  for entry in "${WORKSPACE_APPS[@]}"; do
    install_site_app "${entry%%:*}"
  done

  step "Configuring site"
  bench_exec "bench --site '$SITE_NAME' set-config developer_mode 1"
  bench_exec "bench --site '$SITE_NAME' set-config host_name '$SITE_URL'"
  bench_exec "bench --site '$SITE_NAME' clear-cache"
  success "Developer mode enabled."

  step "Running migrations"
  bench_exec "bench --site '$SITE_NAME' migrate"
  success "Schema up to date."

  step "Starting bench dev server"
  start_bench_server
  wait_for_site
  print_summary
}

if   $DO_STATUS;  then do_status
elif $DO_STOP;    then do_stop
elif $DO_RESTART; then do_stop; do_start
elif $DO_START;   then do_start
else                   do_full_setup
fi
