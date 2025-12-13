#!/bin/bash

# 🚀 Waffen Tactics - Kompletny skrypt startowy
# Uruchamia cały projekt: backend API, frontend React, i Caddy reverse proxy

set -e  # Zakończ skrypt w przypadku błędu

# Kolory do outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funkcja do wyświetlania kolorowych komunikatów
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Ścieżki projektu
PROJECT_ROOT="/home/ubuntu/waffen-tactics-game"
WEB_DIR="$PROJECT_ROOT/waffen-tactics-web"
BACKEND_DIR="$WEB_DIR/backend"

echo "════════════════════════════════════════════════════════"
echo "   🎮 Waffen Tactics - Uruchamianie projektu"
echo "════════════════════════════════════════════════════════"
echo ""

# 1. Sprawdź czy projekt istnieje
if [ ! -d "$PROJECT_ROOT" ]; then
    log_error "Katalog projektu nie istnieje: $PROJECT_ROOT"
    exit 1
fi

# 2. Zatrzymaj istniejące procesy
log_info "Zatrzymywanie istniejących procesów..."
pkill -f "python.*api.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sudo pkill -9 caddy 2>/dev/null || true
sleep 2
log_success "Procesy zatrzymane"

# 3. Sprawdź zależności Node.js
log_info "Sprawdzanie zależności Node.js..."
cd "$WEB_DIR"
if [ ! -d "node_modules" ]; then
    log_warning "node_modules nie istnieją. Instaluję zależności..."
    npm install
    log_success "Zależności zainstalowane"
else
    log_success "node_modules OK"
fi

# 4. Sprawdź Python venv dla backendu
log_info "Sprawdzanie środowiska Python dla backendu..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    log_warning "Brak venv. Tworzę środowisko Python..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    log_success "Środowisko Python utworzone"
else
    log_success "venv OK"
fi

# 5. Sprawdź pliki .env
log_info "Sprawdzanie konfiguracji .env..."
if [ ! -f "$WEB_DIR/.env" ]; then
    log_warning "Brak .env w waffen-tactics-web/"
    log_warning "Tworzę domyślny plik .env..."
    cat > "$WEB_DIR/.env" << 'EOF'
VITE_API_URL=https://waffentactics.pl/api
VITE_DISCORD_CLIENT_ID=1449028504615256217
VITE_DISCORD_REDIRECT_URI=https://waffentactics.pl/auth/callback
EOF
    log_success "Plik .env utworzony"
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
    log_warning "Brak .env w backend/"
    log_warning "Tworzę domyślny plik .env..."
    cat > "$BACKEND_DIR/.env" << 'EOF'
DISCORD_CLIENT_SECRET=beStXjp6g6uvhDCSziYj7_sNuu1wOkda
JWT_SECRET=waffen-tactics-super-secret-jwt-key-2025-production
EOF
    log_success "Plik backend/.env utworzony"
fi

# 6. Uruchom Backend API (Flask - port 8000)
log_info "Uruchamianie Backend API (Flask) na porcie 8000..."
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python3 api.py > api.log 2>&1 &
BACKEND_PID=$!
sleep 3

# Sprawdź czy backend się uruchomił
if ps -p $BACKEND_PID > /dev/null; then
    log_success "Backend API uruchomiony (PID: $BACKEND_PID)"
else
    log_error "Backend API nie uruchomił się poprawnie"
    log_error "Sprawdź logi: tail -f $BACKEND_DIR/api.log"
    exit 1
fi

# 7. Uruchom Frontend (Vite - port 3000)
log_info "Uruchamianie Frontend (Vite) na porcie 3000..."
cd "$WEB_DIR"
nohup npm run dev > vite.log 2>&1 &
FRONTEND_PID=$!
sleep 5

# Sprawdź czy frontend się uruchomił
if ps -p $FRONTEND_PID > /dev/null; then
    log_success "Frontend uruchomiony (PID: $FRONTEND_PID)"
else
    log_error "Frontend nie uruchomił się poprawnie"
    log_error "Sprawdź logi: tail -f $WEB_DIR/vite.log"
    exit 1
fi

# 8. Uruchom Caddy (Reverse Proxy - port 443)
log_info "Uruchamianie Caddy (Reverse Proxy)..."
cd "$WEB_DIR"

# Sprawdź czy Caddy jest zainstalowany
if ! command -v caddy &> /dev/null; then
    log_warning "Caddy nie jest zainstalowany"
    log_warning "Zainstaluj Caddy: https://caddyserver.com/docs/install"
    log_warning "Lub uruchom bez Caddy (tylko development mode na portach 8000 i 3000)"
else
    sudo nohup caddy run --config Caddyfile > caddy.log 2>&1 &
    CADDY_PID=$!
    sleep 3
    
    if sudo pgrep caddy > /dev/null; then
        log_success "Caddy uruchomiony"
    else
        log_warning "Caddy nie uruchomił się (może wymaga uprawnień root)"
        log_warning "Sprawdź logi: tail -f $WEB_DIR/caddy.log"
    fi
fi

# 9. Podsumowanie
echo ""
echo "════════════════════════════════════════════════════════"
log_success "🎉 Projekt uruchomiony pomyślnie!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📍 Dostępne endpointy:"
echo "   • Production:        https://waffentactics.pl"
echo "   • Backend (dev):     http://localhost:8000"
echo "   • Frontend (dev):    http://localhost:3000"
echo ""
echo "📊 Procesy:"
ps aux | grep -E "api.py|vite|caddy" | grep -v grep | awk '{printf "   • PID %-6s %s\n", $2, $11}'
echo ""
echo "📝 Logi:"
echo "   • Backend:  tail -f $BACKEND_DIR/api.log"
echo "   • Frontend: tail -f $WEB_DIR/vite.log"
echo "   • Caddy:    tail -f $WEB_DIR/caddy.log"
echo ""
echo "🛑 Zatrzymanie:"
echo "   pkill -f 'python.*api.py' && pkill -f 'vite' && sudo pkill -9 caddy"
echo ""
echo "════════════════════════════════════════════════════════"
