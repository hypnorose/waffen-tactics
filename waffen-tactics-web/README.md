# Waffen Tactics - React Frontend Setup

## 📋 Wymagania

- Node.js 18+
- npm lub yarn
- Python 3.12+ (dla backendu)

## 🚀 Instalacja Frontend

```bash
cd /home/ubuntu/mentorbot/waffen-tactics-web

# Zainstaluj zależności
npm install

# Stwórz plik .env
cp .env.example .env
```

## 🔑 Konfiguracja Discord OAuth2

1. Idź na: https://discord.com/developers/applications
2. Stwórz nową aplikację lub wybierz istniejącą
3. W zakładce "OAuth2" → "Redirects" dodaj:
   - `http://localhost:3000/auth/callback` (dev)
   - `https://your-domain.com/auth/callback` (produkcja)
4. Skopiuj `Client ID` i `Client Secret`
5. Edytuj plik `.env`:

```env
VITE_DISCORD_CLIENT_ID=your_client_id_here
VITE_DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
VITE_API_URL=http://localhost:8000
```

## 🐍 Instalacja Backend

```bash
cd /home/ubuntu/mentorbot

# Zainstaluj dodatkowe zależności
source bot_venv/bin/activate
pip install fastapi uvicorn[standard] pyjwt aiohttp python-multipart

# Stwórz plik .env dla backendu (jeśli jeszcze nie istnieje)
nano .env
```

Dodaj do `.env`:
```env
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
JWT_SECRET=your-random-secret-key-here
```

## ▶️ Uruchomienie

### Terminal 1 - Backend API:
```bash
cd /home/ubuntu/mentorbot
source bot_venv/bin/activate
python waffen-tactics-backend.py
```
API dostępne na: http://localhost:8000

### Terminal 2 - Frontend React:
```bash
cd /home/ubuntu/mentorbot/waffen-tactics-web
npm run dev
```
Frontend dostępny na: http://localhost:3000 (lub 5173)

## 🎮 Jak używać

1. Otwórz przeglądarkę: http://localhost:3000
2. Kliknij "Zaloguj przez Discord"
3. Zaloguj się na Discord (zostaniesz przekierowany)
4. Graj! ⚔️

## 📁 Struktura Projektu

```
waffen-tactics-web/
├── src/
│   ├── components/     # Komponenty UI (Shop, Bench, Board)
│   ├── pages/          # Strony (Login, Game, Callback)
│   ├── services/       # API calls (axios)
│   ├── store/          # State management (Zustand)
│   ├── App.tsx         # Router
│   └── main.tsx        # Entry point
├── public/
├── package.json
├── vite.config.ts
└── tailwind.config.js

waffen-tactics-backend.py  # FastAPI server
```

## 🔧 Dostępne endpointy API

- `POST /auth/discord/callback` - Wymiana kodu OAuth2 na token
- `GET /auth/me` - Pobierz info o zalogowanym użytkowniku
- `GET /game/state` - Pobierz stan gry
- `POST /game/start` - Rozpocznij nową grę
- `POST /game/buy` - Kup jednostkę
- `POST /game/sell` - Sprzedaj jednostkę
- `POST /game/move-to-board` - Przenieś na planszę
- `POST /game/move-to-bench` - Przenieś na ławkę
- `POST /game/reroll` - Odśwież sklep (2 złota)
- `POST /game/buy-xp` - Kup XP (4 złota)
- `POST /game/combat` - Rozpocznij walkę
- `POST /game/reset` - Resetuj grę
- `GET /game/leaderboard` - Ranking
- `GET /game/units` - Lista wszystkich jednostek

## 🐛 Troubleshooting

### Backend nie startuje:
```bash
# Sprawdź czy port 8000 jest wolny
lsof -i :8000

# Jeśli zajęty, zabij proces:
kill -9 $(lsof -t -i :8000)
```

### Frontend nie startuje:
```bash
# Sprawdź czy port 3000/5173 jest wolny
lsof -i :3000
lsof -i :5173

# Wyczyść cache i reinstaluj:
rm -rf node_modules package-lock.json
npm install
```

### CORS errors:
Upewnij się że backend ma poprawnie skonfigurowany CORS (już jest w kodzie)

### Discord OAuth2 nie działa:
1. Sprawdź czy `DISCORD_CLIENT_ID` i `DISCORD_CLIENT_SECRET` są poprawne
2. Sprawdź czy redirect URI w Discord App = redirect URI w .env
3. Sprawdź logi backendu dla szczegółów błędu

## 📝 TODO

- [ ] WebSocket dla live updates podczas walki
- [ ] Animacje jednostek podczas walki
- [ ] Mobile responsive UI
- [ ] Chat między graczami
- [ ] Replay systemy walk
- [ ] Achievement system

## 🎉 Gotowe!

Teraz masz:
- ✅ Frontend React z Discord login
- ✅ Backend API z pełną funkcjonalnością
- ✅ Integration z istniejącym botem Discord

Gra jest dostępna zarówno przez:
1. Discord bot (`/graj` command)
2. Web interface (localhost:3000)

Oba używają tej samej bazy danych SQLite!
