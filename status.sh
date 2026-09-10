#!/bin/bash

# 📊 Waffen Tactics - Skrypt monitorujący status projektu

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Ścieżki
PROJECT_ROOT="/home/ubuntu/waffen-tactics-game"
WEB_DIR="$PROJECT_ROOT/waffen-tactics-web"
BACKEND_DIR="$WEB_DIR/backend"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/runtime_process_scope.sh"

echo "════════════════════════════════════════════════════════"
echo "   📊 Waffen Tactics - Status projektu"
echo "════════════════════════════════════════════════════════"
echo ""

# Sprawdź procesy
echo -e "${CYAN}🔍 Procesy:${NC}"
BACKEND_RUNNING=$(project_pids_for_cwd "python.*api.py" "$BACKEND_DIR")
FRONTEND_RUNNING=$(project_pids_for_cwd "vite" "$WEB_DIR")
CADDY_RUNNING=$(project_caddy_pids "$WEB_DIR" "Caddyfile")

if [ ! -z "$BACKEND_RUNNING" ]; then
    echo -e "   ${GREEN}✅ Backend API:${NC} uruchomiony (PID: $BACKEND_RUNNING)"
else
    echo -e "   ${RED}❌ Backend API:${NC} zatrzymany"
fi

if [ ! -z "$FRONTEND_RUNNING" ]; then
    echo -e "   ${GREEN}✅ Frontend:${NC} uruchomiony (PID: $FRONTEND_RUNNING)"
else
    echo -e "   ${RED}❌ Frontend:${NC} zatrzymany"
fi

if [ ! -z "$CADDY_RUNNING" ]; then
    echo -e "   ${GREEN}✅ Caddy:${NC} uruchomiony (PID: $CADDY_RUNNING)"
else
    echo -e "   ${RED}❌ Caddy:${NC} zatrzymany"
fi

echo ""

# Sprawdź porty
echo -e "${CYAN}🌐 Porty:${NC}"
PORT_8000=$(netstat -tulpn 2>/dev/null | grep ":8000" || ss -tulpn 2>/dev/null | grep ":8000" || echo "")
PORT_3000=$(netstat -tulpn 2>/dev/null | grep ":3000" || ss -tulpn 2>/dev/null | grep ":3000" || echo "")
PORT_443=$(netstat -tulpn 2>/dev/null | grep ":443" || ss -tulpn 2>/dev/null | grep ":443" || echo "")

if [ ! -z "$PORT_8000" ]; then
    echo -e "   ${GREEN}✅ Port 8000 (Backend):${NC} aktywny"
else
    echo -e "   ${RED}❌ Port 8000 (Backend):${NC} wolny"
fi

if [ ! -z "$PORT_3000" ]; then
    echo -e "   ${GREEN}✅ Port 3000 (Frontend):${NC} aktywny"
else
    echo -e "   ${RED}❌ Port 3000 (Frontend):${NC} wolny"
fi

if [ ! -z "$PORT_443" ]; then
    echo -e "   ${GREEN}✅ Port 443 (HTTPS):${NC} aktywny"
else
    echo -e "   ${RED}❌ Port 443 (HTTPS):${NC} wolny"
fi

echo ""

# Sprawdź dostępność API
echo -e "${CYAN}🔗 Connectivity Tests:${NC}"
if command -v curl &> /dev/null; then
    # Test local backend
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/game/traits 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "   ${GREEN}✅ Backend API:${NC} http://localhost:8000 (HTTP $HTTP_CODE)"
    else
        echo -e "   ${RED}❌ Backend API:${NC} http://localhost:8000 (HTTP $HTTP_CODE)"
    fi

    # Test local frontend
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
        echo -e "   ${GREEN}✅ Frontend:${NC} http://localhost:3000 (HTTP $HTTP_CODE)"
    else
        echo -e "   ${RED}❌ Frontend:${NC} http://localhost:3000 (HTTP $HTTP_CODE)"
    fi
else
    echo -e "   ${YELLOW}⚠️  curl nie zainstalowany - pomiń testy connectivity${NC}"
fi

echo ""

# Ostatnie logi
echo -e "${CYAN}📝 Ostatnie logi (ostatnie 5 linii):${NC}"

if [ -f "$BACKEND_DIR/api.log" ]; then
    echo -e "${BLUE}Backend:${NC}"
    tail -n 5 "$BACKEND_DIR/api.log" | sed 's/^/   /'
else
    echo -e "   ${YELLOW}Brak pliku api.log${NC}"
fi

echo ""

if [ -f "$WEB_DIR/vite.log" ]; then
    echo -e "${BLUE}Frontend:${NC}"
    tail -n 5 "$WEB_DIR/vite.log" | sed 's/^/   /'
else
    echo -e "   ${YELLOW}Brak pliku vite.log${NC}"
fi

echo ""

# Endpointy
echo -e "${CYAN}🌍 Dostępne endpointy:${NC}"
echo "   • Production:     https://waffentactics.pl"
echo "   • Backend (dev):  http://localhost:8000"
echo "   • Frontend (dev): http://localhost:3000"

echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo "💡 Przydatne komendy:"
echo "   • Start:     ./start-all.sh"
echo "   • Stop:      ./stop-all.sh"
echo "   • Status:    ./status.sh"
echo "   • Logi:      tail -f waffen-tactics-web/backend/api.log"
echo ""
