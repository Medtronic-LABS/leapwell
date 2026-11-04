#!/usr/bin/env bash
# Local Frappe bench for the LeapWell Frappe apps (frappe_spice_next_core, leapwell_shukhee_integration).
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
  --stop      docker compose down (data under development/ is kept)
  --restart   --stop, then --start
  --status    container states, HTTP check, MariaDB ping, recent backend logs
  --help      this text

Needs a .env next to this script (cp .env.example .env) and the workspace clones
repos/frappe_spice_next_core and repos/leapwell_shukhee_integration (run /lw-setup).
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BENCH_HOME="/home/frappe/frappe-bench"
# <bench app name>:<workspace clone under ../../repos>, in install order (shukhee requires spice_next_core).
WORKSPACE_APPS=("spice_next_core:frappe_spice_next_core" "shukhee_integration:leapwell_shukhee_integration")

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
  FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-16}"
}

check_workspace_apps() {
  local entry clone
  for entry in "${WORKSPACE_APPS[@]}"; do
    clone="${entry#*:}"
    [[ -d "../../repos/$clone" ]] || error "repos/$clone is missing. Run /lw-setup (or: bash scripts/workspace/setup.sh --only core,shukhee) from the leapwell root."
  done
}

prepare_db_volume() {
  mkdir -p development/workspace
  if [[ "$(uname)" == "Darwin" ]]; then
    if [[ ! -f development/db.sparseimage ]]; then
      info "Creating case-sensitive APFS sparse image for MariaDB (macOS requirement)..."
      mkdir -p development/db
      hdiutil create -size 4g -type SPARSE -fs "Case-sensitive APFS" \
        -volname leapwell-frappe-db development/db
      success "Sparse image created: development/db.sparseimage"
    fi
    if ! mount | grep -q "$(pwd)/development/db"; then
      info "Attaching DB sparse image..."
      hdiutil attach development/db.sparseimage -mountpoint development/db
      success "DB volume mounted at development/db"
    else
      info "DB sparse image already mounted."
    fi
  else
    mkdir -p development/db
  fi
}

wait_for_db() {
  info "Waiting for MariaDB to be ready..."
  local retries=20
  until docker compose exec -T -e MYSQL_PWD="$DB_ROOT_PASSWORD" db mysqladmin ping -h localhost --silent 2>/dev/null; do
    ((retries--)) || error "MariaDB did not become healthy in time."
    sleep 3
  done
  success "MariaDB is ready."
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
  info "Waiting for site at http://localhost:8081 (Frappe takes ~30 s to warm up)..."
  local retries=40
  until curl -sf -o /dev/null "http://localhost:8081"; do
    ((retries--)) || { warn "Site did not respond - check: docker compose exec backend tail -30 /tmp/bench.log"; return; }
    sleep 5
  done
  success "Site is up at http://localhost:8081"
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
  echo -e "  URL      : http://localhost:8081"
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
  info "Checking http://localhost:8081 ..."
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 2>/dev/null || true)
  http_code="${http_code:-000}"
  if [[ "$http_code" == "200" || "$http_code" == "302" || "$http_code" == "301" ]]; then
    success "Web (8081): HTTP $http_code"
  else
    warn "Web (8081): HTTP $http_code - site may still be starting"
  fi

  info "Checking MariaDB ..."
  if docker compose exec -T -e MYSQL_PWD="$DB_ROOT_PASSWORD" db mysqladmin ping -h localhost --silent 2>/dev/null; then
    success "MariaDB: healthy"
  else
    warn "MariaDB: not responding"
  fi

  info "Recent backend logs:"
  docker compose logs --tail 15 backend 2>/dev/null || true
}

do_stop() {
  step "Stopping"
  check_docker
  # compose interpolates .env; give it harmless defaults so a stop works even if .env was removed
  DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-unused-for-stop}" docker compose down
  success "All containers stopped (data under development/ is kept)."
}

ensure_build_deps() {
  docker compose exec -T backend bash -c "
    git config --global --add safe.directory '*'
    dpkg -s python3-dev gcc git nodejs &>/dev/null && command -v yarn &>/dev/null && exit 0
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
  bench_exec "grep -qxF '$app' sites/apps.txt || echo '$app' >> sites/apps.txt"
  bench_exec "grep -qxF '$app' apps.txt 2>/dev/null || echo '$app' >> apps.txt"
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
  prepare_db_volume

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

  prepare_db_volume

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
      "export PATH=\$PATH:/home/frappe/.local/bin; bench init --frappe-branch '$FRAPPE_BRANCH' --skip-redis-config-generation frappe-bench"

    docker compose exec -T backend bash -c "
      cat > $BENCH_HOME/sites/common_site_config.json <<CONF
{
  \"db_host\": \"db\",
  \"db_port\": 3306,
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
    bench_exec "grep -qxF 'frappe_theme' apps.txt || echo 'frappe_theme' >> apps.txt"
    success "frappe_theme fetched."
  fi

  link_workspace_app shukhee_integration

  if site_exists; then
    success "Site '$SITE_NAME' already exists - skipping."
  else
    step "Creating site: $SITE_NAME"
    bench_exec "bench new-site '$SITE_NAME' \
      --db-host db \
      --db-root-password '$DB_ROOT_PASSWORD' \
      --admin-password '$ADMIN_PASSWORD' \
      --no-mariadb-socket"
    success "Site created."
  fi

  install_site_app frappe_theme
  install_site_app spice_next_core
  install_site_app shukhee_integration

  step "Configuring site"
  bench_exec "bench --site '$SITE_NAME' set-config developer_mode 1"
  bench_exec "bench --site '$SITE_NAME' set-config host_name 'http://localhost:8081'"
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
