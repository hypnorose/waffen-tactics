# Wnioski z debugowania systemu logowania

## Problem
Po zalogowaniu przez Discord użytkownik był przekierowywany z powrotem do `/login` zamiast do `/game`.

## Przyczyna
**Niezgodność credentials Discord OAuth:**
- Frontend używał **production DISCORD_CLIENT_ID**: `1449028504615256217`
- Backend był uruchamiany z **development DISCORD_CLIENT_SECRET**: `rh0Pj73TuLDjb-VKpYm5kRwJdW6f-hJv`
- Discord API zwracał błąd `invalid_client` (401) podczas wymiany authorization code

## Rozwiązanie
Backend musi używać **production DISCORD_CLIENT_SECRET** (`OXR2anRAkEOz2ibA-8-BqW6MTz3c7Ch4`) który pasuje do production CLIENT_ID.

## Prawidłowe uruchomienie backend (development mode):
```bash
cd /home/ubuntu/mentorbot/waffen-tactics-web/backend
source venv/bin/activate
DISCORD_CLIENT_SECRET="OXR2anRAkEOz2ibA-8-BqW6MTz3c7Ch4" \
JWT_SECRET="waffen-tactics-jwt-secret-prod" \
nohup python api.py > backend.log 2>&1 &
```

## Prawidłowe uruchomienie frontend (development mode):
```bash
cd /home/ubuntu/mentorbot/waffen-tactics-web
npm run dev -- --host 0.0.0.0
```

## Konfiguracja Discord OAuth
- **Production Client ID**: `1449028504615256217`
- **Production Client Secret**: `OXR2anRAkEOz2ibA-8-BqW6MTz3c7Ch4`
- **Redirect URI**: `https://waffentactics.pl/auth/callback`

## Debugging tips
1. **Logi backend** - dodaj print statements z emoji:
   ```python
   print(f"📥 Auth exchange request: {data}")
   print(f"❌ Discord token error: {response.text}")
   ```

2. **Test endpoint bezpośrednio**:
   ```bash
   curl -X POST http://localhost:8000/auth/exchange \
     -H "Content-Type: application/json" \
     -d '{"code":"test_code"}'
   ```

3. **Sprawdź proces**:
   ```bash
   ps aux | grep "[p]ython.*api.py"
   tail -f backend/backend.log
   ```

4. **Hot reload nie działa** - zawsze restartuj backend po zmianach w kodzie:
   ```bash
   pkill -9 -f "python.*api.py"
   ```

## Wspólny system walki
Logika walki jest współdzielona między Discord bot i web version:
- **Shared module**: `/waffen-tactics-web/backend/combat.py`
  - `CombatSimulator` - tick-based combat z attack speed
  - `CombatUnit` - lightweight unit representation
  
- **Web backend**: importuje `from combat import CombatSimulator, CombatUnit`
- **Discord bot**: wrapper w `/waffen-tactics/src/waffen_tactics/services/combat.py`

Zmiana w `combat.py` automatycznie wpływa na obie wersje gry.

## Combat mechanics
- **Attack speed based**: jednostki atakują asynchronicznie (nie round-by-round)
- **Targeting**: 60% priorytet na highest defense, 40% random
- **Damage**: `max(1, attack - defense)`
- **Time step**: dt=0.1s dla symulacji, timeout 60-120s

## Kluczowe pliki
- `/waffen-tactics-web/backend/api.py` - Flask API
- `/waffen-tactics-web/backend/combat.py` - shared combat logic
- `/waffen-tactics-web/src/components/CombatOverlay.tsx` - UI walki
- `/waffen-tactics-web/.env` - VITE_API_URL config
- `/waffen-tactics-web/Caddyfile` - proxy: vite (port 3000) + backend (port 8000)
