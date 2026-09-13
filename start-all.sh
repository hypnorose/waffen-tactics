#!/bin/bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}INFO${NC} $1"
}

log_success() {
    echo -e "${GREEN}OK${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}WARN${NC} $1"
}

log_error() {
    echo -e "${RED}ERR${NC} $1"
}

require_key() {
    local file="$1"
    local key="$2"
    if ! grep -Eq "^[[:space:]]*${key}=[^[:space:]]+" "$file"; then
        log_error "Missing required config: $key in $file"
        exit 1
    fi
}

load_nvm() {
    export NVM_DIR="$HOME/.nvm"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        . "$NVM_DIR/nvm.sh"
    fi

    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js is not available after loading nvm"
        exit 1
    fi

    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm is not available after loading nvm"
        exit 1
    fi
}

PROJECT_ROOT="/home/ubuntu/waffen-tactics-game"
WEB_DIR="$PROJECT_ROOT/waffen-tactics-web"
BACKEND_DIR="$WEB_DIR/backend"
API_HOST="127.0.0.1"
API_PORT="8000"
CADDY_SERVICE="${CADDY_SERVICE:-waffentactics-caddy.service}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/runtime_process_scope.sh"

require_caddy_service() {
    if ! command -v systemctl >/dev/null 2>&1; then
        log_error "systemctl is required; refusing to start unmanaged Caddy"
        return 1
    fi
    if ! sudo -n systemctl cat "$CADDY_SERVICE" >/dev/null 2>&1; then
        log_error "Missing managed Caddy service: $CADDY_SERVICE"
        log_error "Install ops/systemd/waffentactics-caddy.service before starting production"
        return 1
    fi
}

echo "=============================================="
echo " Waffen Tactics - start"
echo "=============================================="

if [ ! -d "$PROJECT_ROOT" ]; then
    log_error "Project directory does not exist: $PROJECT_ROOT"
    exit 1
fi

if ! require_caddy_service; then
    exit 1
fi

log_info "Stopping existing project processes"
while IFS= read -r pid; do
    kill "$pid" 2>/dev/null || true
    log_info "Stopped backend pid=$pid"
done < <(project_backend_pids)
while IFS= read -r pid; do
    kill "$pid" 2>/dev/null || true
    log_info "Stopped frontend pid=$pid"
done < <(project_pids_for_cwd "vite" "$WEB_DIR")

if sudo -n systemctl is-active --quiet "$CADDY_SERVICE"; then
    sudo -n systemctl stop "$CADDY_SERVICE"
    log_info "Stopped managed Caddy service=$CADDY_SERVICE"
fi

while IFS= read -r pid; do
    sudo -n kill "$pid" 2>/dev/null || true
    log_info "Stopped project Caddy pid=$pid"
done < <(project_caddy_pids "$WEB_DIR" "Caddyfile")

for attempt in 1 2 3 4 5; do
    if [ -z "$(project_caddy_pids "$WEB_DIR" "Caddyfile")" ]; then
        break
    fi
    sleep 1
done
if [ -n "$(project_caddy_pids "$WEB_DIR" "Caddyfile")" ]; then
    log_error "Project Caddy did not stop; refusing to start a duplicate"
    exit 1
fi
sleep 2
log_success "Existing processes stopped"

log_info "Checking frontend config"
cd "$WEB_DIR"
if [ ! -f ".env" ]; then
    log_error "Missing $WEB_DIR/.env"
    log_error "Copy .env.example and set VITE_API_URL, VITE_DISCORD_CLIENT_ID, VITE_DISCORD_REDIRECT_URI."
    exit 1
fi
require_key "$WEB_DIR/.env" "VITE_API_URL"
require_key "$WEB_DIR/.env" "VITE_DISCORD_CLIENT_ID"
require_key "$WEB_DIR/.env" "VITE_DISCORD_REDIRECT_URI"
log_success "Frontend env ok"

if [ ! -d "node_modules" ]; then
    log_error "Missing $WEB_DIR/node_modules"
    log_error "Install frontend dependencies before starting the runtime."
    exit 1
fi

log_info "Checking backend config"
cd "$BACKEND_DIR"
if [ ! -f ".env" ]; then
    log_error "Missing $BACKEND_DIR/.env"
    log_error "Copy backend/.env.example and set DISCORD_CLIENT_SECRET and JWT_SECRET."
    exit 1
fi
require_key "$BACKEND_DIR/.env" "DISCORD_CLIENT_SECRET"
require_key "$BACKEND_DIR/.env" "JWT_SECRET"
log_success "Backend env ok"

if [ ! -d "venv" ]; then
    log_error "Missing $BACKEND_DIR/venv"
    log_error "Create the backend virtualenv before starting the runtime."
    exit 1
fi

log_info "Loading Node runtime"
load_nvm
log_success "Node runtime ready"

log_info "Building frontend production bundle"
cd "$WEB_DIR"
if ! npm run build > frontend-build.log 2>&1; then
    log_error "Frontend production build failed"
    tail -n 40 frontend-build.log | sed 's/^/   /' || true
    exit 1
fi
log_success "Frontend production bundle ready"

if [ ! -s "$WEB_DIR/dist/index.html" ]; then
    log_error "Frontend production artifact is missing: $WEB_DIR/dist/index.html"
    exit 1
fi
log_success "Frontend static artifact ready"

log_info "Starting backend API on port 8000"
cd "$BACKEND_DIR"
source venv/bin/activate
if ! command -v gunicorn >/dev/null 2>&1; then
    log_error "gunicorn is not installed in $BACKEND_DIR/venv"
    log_error "Install backend requirements before starting production."
    exit 1
fi
nohup gunicorn \
    --chdir "$BACKEND_DIR" \
    --bind "$API_HOST:$API_PORT" \
    --workers 1 \
    --threads 8 \
    --timeout 180 \
    --preload \
    --capture-output \
    --access-logfile - \
    --error-logfile - \
    wsgi:app > api.log 2>&1 &
BACKEND_PID=$!
sleep 3
if ps -p "$BACKEND_PID" > /dev/null; then
    log_success "Backend started pid=$BACKEND_PID"
else
    log_error "Backend failed to start"
    exit 1
fi

log_info "Starting managed Caddy service=$CADDY_SERVICE"
if ! sudo -n systemctl restart "$CADDY_SERVICE"; then
    log_error "Managed Caddy service failed to start"
    exit 1
fi
if sudo -n systemctl is-active --quiet "$CADDY_SERVICE"; then
    log_success "Caddy started under systemd"
else
    log_error "Managed Caddy service is not active"
    exit 1
fi

echo ""
echo "=============================================="
log_success "Project started"
echo "=============================================="
echo "Production: https://waffentactics.pl"
echo "Backend WSGI: http://localhost:8000"
echo "Frontend static: $WEB_DIR/dist"
echo ""
echo "Processes:"
ps aux | grep -E "api.py|gunicorn|vite|caddy" | grep -v grep | awk '{printf "  PID %-6s %s\n", $2, $11}'
echo ""
echo "Logs:"
echo "  Backend:  tail -f $BACKEND_DIR/api.log"
echo "  Frontend: tail -f $WEB_DIR/frontend-build.log"
echo "  Caddy:    journalctl -u $CADDY_SERVICE -f"
echo ""
