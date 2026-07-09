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

PROJECT_ROOT="/home/ubuntu/waffen-tactics-game"
WEB_DIR="$PROJECT_ROOT/waffen-tactics-web"
BACKEND_DIR="$WEB_DIR/backend"

echo "=============================================="
echo " Waffen Tactics - start"
echo "=============================================="

if [ ! -d "$PROJECT_ROOT" ]; then
    log_error "Project directory does not exist: $PROJECT_ROOT"
    exit 1
fi

log_info "Stopping existing project processes"
for pid in $(pgrep -f "api.py" 2>/dev/null || true); do
    if [ -L "/proc/$pid/cwd" ] && readlink "/proc/$pid/cwd" 2>/dev/null | grep -q "$BACKEND_DIR"; then
        kill "$pid" 2>/dev/null || true
        log_info "Stopped backend pid=$pid"
    fi
done
for pid in $(pgrep -f "vite" 2>/dev/null || true); do
    if [ -L "/proc/$pid/cwd" ] && readlink "/proc/$pid/cwd" 2>/dev/null | grep -q "$WEB_DIR"; then
        kill "$pid" 2>/dev/null || true
        log_info "Stopped frontend pid=$pid"
    fi
done
if pgrep -a caddy 2>/dev/null | grep -q "$WEB_DIR/Caddyfile"; then
    sudo pkill -f "caddy.*$WEB_DIR/Caddyfile" 2>/dev/null || true
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

log_info "Starting backend API on port 8000"
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python3 api.py > api.log 2>&1 &
BACKEND_PID=$!
sleep 3
if ps -p "$BACKEND_PID" > /dev/null; then
    log_success "Backend started pid=$BACKEND_PID"
else
    log_error "Backend failed to start"
    exit 1
fi

log_info "Starting frontend on port 3000"
cd "$WEB_DIR"
nohup npm run dev > vite.log 2>&1 &
FRONTEND_PID=$!
sleep 5
if ps -p "$FRONTEND_PID" > /dev/null; then
    log_success "Frontend started pid=$FRONTEND_PID"
else
    log_error "Frontend failed to start"
    exit 1
fi

log_info "Starting Caddy"
cd "$WEB_DIR"
if ! command -v caddy >/dev/null 2>&1; then
    log_warning "Caddy is not installed"
else
    sudo nohup caddy run --config Caddyfile > caddy.log 2>&1 &
    sleep 3
    if sudo pgrep caddy >/dev/null 2>&1; then
        log_success "Caddy started"
    else
        log_warning "Caddy did not start"
    fi
fi

echo ""
echo "=============================================="
log_success "Project started"
echo "=============================================="
echo "Production: https://waffentactics.pl"
echo "Backend dev: http://localhost:8000"
echo "Frontend dev: http://localhost:3000"
echo ""
echo "Processes:"
ps aux | grep -E "api.py|vite|caddy" | grep -v grep | awk '{printf "  PID %-6s %s\n", $2, $11}'
echo ""
echo "Logs:"
echo "  Backend:  tail -f $BACKEND_DIR/api.log"
echo "  Frontend: tail -f $WEB_DIR/vite.log"
echo "  Caddy:    tail -f $WEB_DIR/caddy.log"
echo ""
