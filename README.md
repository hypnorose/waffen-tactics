# Waffen Tactics Game - Production Environment

## 📂 Struktura Projektu

```
/home/ubuntu/waffen-tactics-game/
├── waffen-tactics/              # Backend + Bot Discord
│   ├── units.json               # Definicje jednostek
│   ├── traits.json              # Definicje synergii
│   ├── waffen_tactics_game.db   # Baza SQLite
│   └── src/waffen_tactics/      # Kod Python
└── waffen-tactics-web/          # Frontend + API Web
    ├── backend/api.py           # Flask API (port 8000)
    ├── src/                     # React + TypeScript
    ├── Caddyfile                # Reverse proxy config
    └── .env                     # Zmienne środowiskowe
```

## 🚀 Uruchamianie

### Backend API (Flask - port 8000)
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web
nohup python3 backend/api.py > backend/api.log 2>&1 &
```

### Frontend (Vite - port 3000)
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web
nohup npm run dev > vite.log 2>&1 &
```

### Reverse Proxy (Caddy - port 443)
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web
sudo nohup caddy run --config Caddyfile > caddy.log 2>&1 &
```

## 🛑 Zatrzymywanie

```bash
pkill -f "python.*api.py"  # Backend
pkill -f "vite"            # Frontend
sudo pkill -9 caddy        # Caddy
```

## 🔍 Monitorowanie

```bash
# Logi backend
tail -f /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend/api.log

# Logi frontend
tail -f /home/ubuntu/waffen-tactics-game/waffen-tactics-web/vite.log

# Logi Caddy
tail -f /home/ubuntu/waffen-tactics-game/waffen-tactics-web/caddy.log

# Sprawdź procesy
ps aux | grep -E "api.py|vite|caddy" | grep -v grep
```

## 🌐 Dostęp

- **Produkcja**: https://waffentactics.pl
- **API Endpoint**: https://waffentactics.pl/api
- **Bezpośredni backend**: http://localhost:8000
- **Bezpośredni frontend**: http://localhost:3000

## 🔧 Konfiguracja

### .env (waffen-tactics-web/.env)
```
VITE_API_URL=https://waffentactics.pl/api
VITE_DISCORD_CLIENT_ID=1449028504615256217
VITE_DISCORD_REDIRECT_URI=https://waffentactics.pl/auth/callback
DISCORD_CLIENT_SECRET=beStXjp6g6uvhDCSziYj7_sNuu1wOkda
JWT_SECRET=waffen-tactics-super-secret-jwt-key-2025-production
```

## 📝 Ważne uwagi

1. **Zmiany w units.json**: Wymagają restartu backendu (GameManager ładuje dane przy starcie)
2. **Zmiany w frontendzie**: Użytkownicy muszą odświeżyć przeglądarkę (Ctrl+F5)
3. **Baza danych**: Lokalizacja `/home/ubuntu/waffen-tactics-game/waffen-tactics/waffen_tactics_game.db`
4. **Backup**: Backend automatycznie tworzy kopie zapasowe bazy przed modyfikacją

## 🐛 Troubleshooting

### Backend nie odpowiada
```bash
tail -50 /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend/api.log
# Restart:
pkill -f "api.py" && cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web && nohup python3 backend/api.py > backend/api.log 2>&1 &
```

### Frontend nie ładuje jednostek
1. Sprawdź czy backend działa: `curl http://localhost:8000/game/traits`
2. Odśwież cache przeglądarki: Ctrl+Shift+Delete
3. Hard refresh: Ctrl+F5

### Caddy błędy certyfikatu
```bash
sudo caddy validate --config /home/ubuntu/waffen-tactics-game/waffen-tactics-web/Caddyfile
```

## 📊 Status System

Sprawdź czy wszystko działa:
```bash
curl -s http://localhost:8000/game/traits | jq '.[0]'  # Test API
curl -I https://waffentactics.pl                      # Test HTTPS
```
