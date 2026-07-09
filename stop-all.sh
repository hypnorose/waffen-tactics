#!/bin/bash

# 🛑 Waffen Tactics - Skrypt zatrzymujący wszystkie procesy

# Kolory do outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

PROJECT_ROOT="/home/ubuntu/waffen-tactics-game"
WEB_DIR="$PROJECT_ROOT/waffen-tactics-web"
BACKEND_DIR="$WEB_DIR/backend"

echo "════════════════════════════════════════════════════════"
echo "   🛑 Waffen Tactics - Zatrzymywanie projektu"
echo "════════════════════════════════════════════════════════"
echo ""

# Pokaż co będzie zatrzymane
log_info "Aktywne procesy przed zatrzymaniem:"
ps aux | grep -E "api.py|vite|caddy" | grep -v grep | awk '{printf "   • PID %-6s %s\n", $2, $11}' || echo "   (brak procesów)"
echo ""

# Zatrzymaj Backend API - tylko ten projekt
log_info "Zatrzymywanie Backend API..."
_stopped=0
for pid in $(pgrep -f "api.py" 2>/dev/null); do
    if [ -L "/proc/$pid/cwd" ] && readlink "/proc/$pid/cwd" 2>/dev/null | grep -q "$BACKEND_DIR"; then
        kill "$pid" 2>/dev/null && _stopped=1 && log_info "Zatrzymano Backend PID=$pid"
    fi
done
[ "$_stopped" -eq 1 ] && log_success "Backend zatrzymany" || log_info "Backend nie był uruchomiony"

# Zatrzymaj Frontend - tylko ten projekt
log_info "Zatrzymywanie Frontend (Vite)..."
_stopped=0
for pid in $(pgrep -f "vite" 2>/dev/null); do
    if [ -L "/proc/$pid/cwd" ] && readlink "/proc/$pid/cwd" 2>/dev/null | grep -q "$WEB_DIR"; then
        kill "$pid" 2>/dev/null && _stopped=1 && log_info "Zatrzymano Frontend PID=$pid"
    fi
done
[ "$_stopped" -eq 1 ] && log_success "Frontend zatrzymany" || log_info "Frontend nie był uruchomiony"

# Zatrzymaj Caddy - tylko jeśli uruchomiony z Caddyfile tego projektu
log_info "Zatrzymywanie Caddy..."
if pgrep -a caddy 2>/dev/null | grep -q "$WEB_DIR/Caddyfile"; then
    sudo pkill -f "caddy.*$WEB_DIR/Caddyfile" 2>/dev/null && log_success "Caddy zatrzymany" || log_info "Caddy nie był uruchomiony"
else
    log_info "Caddy nie był uruchomiony przez ten projekt"
fi

sleep 2

# Sprawdź czy wszystko zostało zatrzymane
echo ""
log_info "Sprawdzanie pozostałych procesów..."
REMAINING=$(ps aux | grep -E "api.py|vite|caddy" | grep -v grep)

if [ -z "$REMAINING" ]; then
    log_success "Wszystkie procesy zatrzymane pomyślnie"
else
    echo ""
    echo "⚠️  Pozostałe procesy:"
    echo "$REMAINING"
fi

echo ""
echo "════════════════════════════════════════════════════════"
