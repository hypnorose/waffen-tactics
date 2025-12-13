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

echo "════════════════════════════════════════════════════════"
echo "   🛑 Waffen Tactics - Zatrzymywanie projektu"
echo "════════════════════════════════════════════════════════"
echo ""

# Pokaż co będzie zatrzymane
log_info "Aktywne procesy przed zatrzymaniem:"
ps aux | grep -E "api.py|vite|caddy" | grep -v grep | awk '{printf "   • PID %-6s %s\n", $2, $11}' || echo "   (brak procesów)"
echo ""

# Zatrzymaj Backend API
log_info "Zatrzymywanie Backend API..."
pkill -f "python.*api.py" 2>/dev/null && log_success "Backend zatrzymany" || log_info "Backend nie był uruchomiony"

# Zatrzymaj Frontend
log_info "Zatrzymywanie Frontend (Vite)..."
pkill -f "vite" 2>/dev/null && log_success "Frontend zatrzymany" || log_info "Frontend nie był uruchomiony"

# Zatrzymaj Caddy
log_info "Zatrzymywanie Caddy..."
sudo pkill -9 caddy 2>/dev/null && log_success "Caddy zatrzymany" || log_info "Caddy nie był uruchomiony"

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
