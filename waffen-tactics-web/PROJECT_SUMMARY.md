# Waffen Tactics - Project Summary

## Overview
Waffen Tactics to auto-battler game dostępny w dwóch wersjach:
1. **Discord Bot** - oryginalna wersja tekstowa
2. **Web Application** - wizualna wersja z pełnym UI

Obie wersje **współdzielą tą samą logikę gry** z repozytorium `waffen-tactics`.

## Architecture

### Core Game Logic (Shared)
Lokalizacja: `/home/ubuntu/mentorbot/waffen-tactics/src/waffen_tactics/`

**Główne moduły:**
- `models/player_state.py` - Stan gracza (złoto, XP, poziom, board, bench, shop)
- `services/game_manager.py` - Główny manager gry (kupowanie, sprzedawanie, levelup)
- `services/database.py` - DatabaseManager dla PostgreSQL (tabele: user_states, opponent_teams)
- `data/units.json` - Baza danych wszystkich jednostek z statystykami
- `data/traits.json` - System synergii (factions & classes)

**Kluczowe koncepty:**
- Board: max jednostek = level gracza
- Bench: max 9 jednostek
- Shop: 5 slotów, odświeżanie za 2 złota
- Kombinowanie: 3 identyczne jednostki → upgrade star level
- Gold income: 5 base + min(5, gold//10) interest + 1 za wygraną
- XP: +2 per combat, level up gdy xp >= level*2

### Combat System (Shared)
Lokalizacja: `/home/ubuntu/mentorbot/waffen-tactics-web/backend/combat.py`

**Współdzielony kod walki:**
```python
class CombatUnit:
    # Lightweight unit dla symulacji
    id, name, hp, max_hp, attack, defense, attack_speed

class CombatSimulator:
    # Tick-based combat (10 ticków/sekundę)
    # Attack speed: szybsze jednostki atakują częściej
    # Damage = max(1, attack - target.defense)
    # Losowy wybór celu (tylko żywe jednostki)
```

**Użycie:**
- Discord bot: `copy_bot.py` importuje i używa
- Web backend: `api.py` importuje i używa przez SSE streaming

### Web Backend
Lokalizacja: `/home/ubuntu/mentorbot/waffen-tactics-web/backend/api.py`

**Stack:**
- Flask + Flask-CORS
- Server-Sent Events (SSE) dla live combat
- JWT authentication
- Discord OAuth2
- Port: 8000

**Kluczowe endpointy:**

1. **Authentication:**
   - `POST /auth/discord` - wymiana Discord code za JWT token
   - Uses: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`

2. **Game State:**
   - `GET /api/state` - pobierz stan gracza (requires JWT)
   - Uses: `DatabaseManager` + `GameManager` z waffen-tactics

3. **Actions:**
   - `POST /api/buy-unit` - kup jednostkę ze shopu
   - `POST /api/sell-unit` - sprzedaj jednostkę
   - `POST /api/reroll` - odśwież shop (2 gold)
   - `POST /api/buy-xp` - kup 4 XP (4 gold)
   - `POST /api/move-to-board` - przenieś z bench na board
   - `POST /api/move-to-bench` - przenieś z board na bench

4. **Combat:**
   - `GET /api/combat/start` - rozpocznij walkę (SSE stream)
   - **Flow:**
     1. Załaduj stan gracza z DB
     2. Znajdź przeciwnika z `opponent_teams` (najbliższa liczba wygranych)
     3. Oblicz synergies dla obu teamów
     4. Użyj `CombatSimulator` do symulacji
     5. Streamuj eventy: units_init, unit_attack, unit_death, combat_end
     6. Po walce: update gold (+1 win, interest, +5 base), XP (+2), saves, level up
     7. Zapisz team do `opponent_teams` dla matchmakingu
     8. Wygeneruj nowy shop

**Database Tables:**
- `user_states` - persistentny stan każdego gracza (JSON)
- `opponent_teams` - pool przeciwników (user_id, nickname, team_json, wins, level)

### Web Frontend
Lokalizacja: `/home/ubuntu/mentorbot/waffen-tactics-web/src/`

**Stack:**
- React 18 + TypeScript
- Vite dev server (port 3000)
- TailwindCSS
- Zustand (state management)
- React Router

**Główne komponenty:**

1. **Auth Pages:**
   - `Login.tsx` - przycisk "Zaloguj przez Discord"
   - `AuthCallback.tsx` - odbiera code, wymienia na JWT, zapisuje w localStorage

2. **Game Pages:**
   - `Game.tsx` - główny kontener gry
   - Shows: header (gold, XP, level), GameBoard, Bench, Shop, buttons

3. **Game Components:**
   - `GameBoard.tsx` - wyświetla board units + synergies
     - Flex-wrap layout (wrapping, no scroll)
     - Synergies z kolorami tier (green/blue/purple/orange)
     - Move to bench buttons
   
   - `Bench.tsx` - wyświetla bench units
     - Flex-wrap layout
     - Move to board + sell buttons
   
   - `Shop.tsx` - wyświetla 5 slotów shopu
     - **Horizontal scroll** (overflow-x-auto)
     - Buy unit, reroll, buy XP buttons
     - Shop odds display
   
   - `UnitCard.tsx` - wyświetla pojedynczą jednostkę
     - Name, star level, cost, factions, classes
     - Rarity colors based on cost:
       - Cost 1: gray (#6b7280)
       - Cost 2: green (#10b981)
       - Cost 3: blue (#3b82f6)
       - Cost 4: purple (#a855f7)
       - Cost 5: orange (#f59e0b)
   
   - `CombatOverlay.tsx` - fullscreen combat display
     - Size: 1400x850px
     - SSE connection do `/api/combat/start`
     - Real-time updates: HP bars, death animations
     - Shows: opponent info (name, level, wins)
     - Synergies display z tier colors
     - Combat log (100px height, toggle hide/show)
     - Speed: 0.15s per attack, 0.1s per death

**State Management:**
- `authStore.ts` - token, user info
- `gameStore.ts` - playerState, loading states

**Data:**
- `units.ts` - imports z `/waffen-tactics/data/units.json`
- `traits.ts` - imports z `/waffen-tactics/data/traits.json`

### Discord Bot
Lokalizacja: `/home/ubuntu/mentorbot/copy_bot.py`

**Używa tych samych modułów:**
```python
sys.path.insert(0, str(Path(__file__).parent / 'waffen-tactics' / 'src'))
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from combat import CombatSimulator
```

**Commands:**
- `/start` - inicjalizacja gracza
- `/board` - pokaż planszę
- `/shop` - pokaż shop
- `/buy <slot>` - kup jednostkę
- `/sell <index>` - sprzedaj jednostkę
- `/reroll` - odśwież shop
- `/combat` - rozpocznij walkę (używa CombatSimulator)

## Deployment

### Backend (Flask)
```bash
cd /home/ubuntu/mentorbot/waffen-tactics-web/backend
python api.py
# Runs on port 8000
```

**Environment Variables:**
- `DISCORD_CLIENT_SECRET` - Discord OAuth secret
- `JWT_SECRET` - JWT signing key
- `DATABASE_URL` - PostgreSQL connection string

### Frontend (Vite)
```bash
cd /home/ubuntu/mentorbot/waffen-tactics-web
npm run dev
# Runs on port 3000
```

### Discord Bot
```bash
cd /home/ubuntu/mentorbot
python copy_bot.py
```

**Environment:**
- `DISCORD_BOT_TOKEN` - bot token
- Same database as web version

## Key Design Decisions

### 1. Shared Core Logic
**Why:** Zapewnia consistency między Discord botem a webem. Zmiany w balansie/mechanikach automatycznie działają w obu wersjach.

**Implementation:**
- Web backend importuje z `/waffen-tactics/src/waffen_tactics/`
- Discord bot importuje z tego samego miejsca
- Shared `combat.py` dla identycznej logiki walki

### 2. Separate Combat Module
**Why:** Combat jest zbyt złożony żeby duplikować. SSE streaming wymaga event-based architektury.

**Implementation:**
- `combat.py` w `/waffen-tactics-web/backend/`
- Discord bot i web backend importują ten sam moduł
- CombatSimulator ma callback system dla eventów

### 3. Opponent Teams Database
**Why:** Potrzebujemy pool przeciwników dla matchmakingu. Bot gracze mogą walczyć przeciwko web graczom i vice versa.

**Implementation:**
- Tabela `opponent_teams`: user_id, nickname, team_json, wins, level
- Po każdej walce: save current team
- Przed walką: load opponent z closest win count
- Cross-platform matchmaking (Discord vs Web)

### 4. Server-Sent Events for Combat
**Why:** WebSocket byłby overkill. SSE jest prostsze dla one-way streaming (server → client).

**Implementation:**
- `/api/combat/start` zwraca `text/event-stream`
- Events: units_init, unit_attack, unit_death, combat_end
- Frontend: EventSource API do consumingu
- Real-time updates HP bars i combat log

### 5. JWT Authentication
**Why:** Discord OAuth wymaga bezpiecznej wymiany tokenów. JWT przechowuje user_id dla API calls.

**Implementation:**
- Discord OAuth flow → JWT token
- Frontend: przechowuje w localStorage
- Backend: middleware sprawdza JWT na każdym protected endpoint

### 6. Rarity Colors
**Why:** Visual feedback dla wartości jednostek. Cost = rarity.

**Implementation:**
- Cost-based coloring (1-5)
- Borders + glows w combat
- Consistent w całym UI

### 7. Tier-Based Synergy Colors
**Why:** Wizualne pokazanie siły synergii (inactive → max tier).

**Implementation:**
- Count-based tier calculation: 2/3/4/6+ = T1/T2/T3/T4
- Colors: gray (T0) → green (T1) → blue (T2) → purple (T3) → orange (T4)
- Używane w GameBoard i CombatOverlay

## Combat Flow (Detailed)

### 1. Pre-Combat
```python
# Load player state
player = await db_manager.get_player_state(user_id)

# Find opponent
opponent_data = await db_manager.get_random_opponent(player.wins)

# Calculate synergies
player_synergies = calculate_synergies(player.board)
opponent_synergies = calculate_synergies(opponent_team)
```

### 2. Combat Initialization
```python
simulator = CombatSimulator()

# Convert to CombatUnit
player_units = [CombatUnit(...) for unit in player.board]
opponent_units = [CombatUnit(...) for unit in opponent_team]

# Stream units_init event
yield f"data: {json.dumps(event)}\n\n"
```

### 3. Combat Loop
```python
# Tick-based system (10 ticks/second)
tick = 0
while both teams alive and tick < 3000:
    tick += 1
    
    # Check each unit's next attack
    for unit in all_units:
        if tick >= unit.next_attack_tick:
            target = random.choice(alive_enemies)
            damage = max(1, unit.attack - target.defense)
            target.hp -= damage
            
            # Stream unit_attack event
            yield attack_event
            
            if target.hp <= 0:
                # Stream unit_death event
                yield death_event
            
            unit.next_attack_tick = tick + (10 / unit.attack_speed)
```

### 4. Post-Combat
```python
# Determine winner
winner = "player" if opponent_team_dead else "opponent"

# Update player
if winner == "player":
    player.wins += 1
    player.gold += 1  # Win bonus

# Calculate interest
interest = min(5, player.gold // 10)
player.gold += 5 + interest

# XP
player.xp += 2
while player.xp >= player.level * 2:
    player.xp -= player.level * 2
    player.level += 1
    player.max_board_size = player.level

# Save state
await db_manager.save_player_state(player)

# Save team to opponent pool
await db_manager.save_opponent_team(
    user_id, username, player.board, player.wins, player.level
)

# Generate new shop
player.last_shop = [random_unit_by_level() for _ in range(5)]

# Stream combat_end event
yield final_event
```

## Common Issues & Solutions

### Issue 1: "No token found"
**Cause:** JWT token missing/expired w localStorage
**Solution:** Logout i re-login przez Discord OAuth

### Issue 2: "Cannot find opponent"
**Cause:** `opponent_teams` table pusty
**Solution:** Po pierwszej walce, team jest zapisywany. Potrzeba kilka graczy żeby zbudować pool.

### Issue 3: Combat nie startuje
**Cause:** Board jest pusty lub backend down
**Solution:** 
- Check backend running on port 8000
- Ensure board has units

### Issue 4: Shop slots pusty
**Cause:** `last_shop` w state jest null/empty
**Solution:** Backend automatycznie generuje shop po combat/reroll

### Issue 5: Synergies nie pokazują tier
**Cause:** Frontend nie oblicza tier z count
**Solution:** Tier calculation: count >= 6 ? T4 : count >= 4 ? T3 : etc.

## File Structure
```
/home/ubuntu/mentorbot/
├── waffen-tactics/                    # Core game logic (shared)
│   └── src/waffen_tactics/
│       ├── models/
│       │   └── player_state.py        # PlayerState class
│       ├── services/
│       │   ├── database.py            # DatabaseManager
│       │   └── game_manager.py        # GameManager
│       └── data/
│           ├── units.json             # All unit definitions
│           └── traits.json            # Synergy system
│
├── waffen-tactics-web/                # Web version
│   ├── backend/
│   │   ├── api.py                     # Flask API (port 8000)
│   │   └── combat.py                  # Shared combat logic
│   └── src/
│       ├── components/
│       │   ├── GameBoard.tsx          # Board + synergies
│       │   ├── Bench.tsx              # Bench units
│       │   ├── Shop.tsx               # Shop (horizontal scroll)
│       │   ├── UnitCard.tsx           # Unit display
│       │   └── CombatOverlay.tsx      # Combat screen (SSE)
│       ├── pages/
│       │   ├── Login.tsx              # Discord OAuth
│       │   ├── AuthCallback.tsx       # OAuth callback
│       │   └── Game.tsx               # Main game page
│       ├── store/
│       │   ├── authStore.ts           # Auth state (Zustand)
│       │   └── gameStore.ts           # Game state (Zustand)
│       └── data/
│           ├── units.ts               # Import from waffen-tactics
│           └── traits.ts              # Import from waffen-tactics
│
└── copy_bot.py                        # Discord bot (uses waffen-tactics)
```

## Database Schema

### user_states
```sql
CREATE TABLE user_states (
    user_id VARCHAR(255) PRIMARY KEY,
    state_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**state_json structure:**
```json
{
  "user_id": "123456789",
  "gold": 10,
  "level": 3,
  "xp": 2,
  "wins": 5,
  "board": [
    {"instance_id": "uuid", "unit_id": "soldier", "star_level": 1}
  ],
  "bench": [...],
  "last_shop": ["soldier", "archer", null, "mage", null],
  "max_board_size": 3,
  "max_bench_size": 9
}
```

### opponent_teams
```sql
CREATE TABLE opponent_teams (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    nickname VARCHAR(255) NOT NULL,
    team_json TEXT NOT NULL,
    wins INT DEFAULT 0,
    level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**team_json structure:**
```json
[
  {"unit_id": "soldier", "star_level": 2},
  {"unit_id": "archer", "star_level": 1}
]
```

## Configuration Files

### Backend Environment
```bash
# .env (backend)
DISCORD_CLIENT_SECRET=your_discord_secret
JWT_SECRET=your_jwt_secret
DATABASE_URL=postgresql://user:pass@localhost/waffen_tactics
```

### Frontend Environment
```bash
# .env (frontend)
VITE_API_URL=http://localhost:8000
VITE_DISCORD_CLIENT_ID=1449028504615256217
VITE_REDIRECT_URI=http://localhost:3000/auth/callback
```

### Discord Bot Environment
```bash
# .env (bot)
DISCORD_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost/waffen_tactics
```

## Testing Checklist

### Backend
- [ ] `/api/state` returns player state with JWT
- [ ] `/api/buy-unit` modifies board/bench correctly
- [ ] `/api/combat/start` streams SSE events
- [ ] Gold calculation: 5 + interest + win bonus
- [ ] XP gives +2 per combat, auto level up
- [ ] Opponent teams saved after combat
- [ ] Shop regeneration after combat

### Frontend
- [ ] Login redirects to Discord OAuth
- [ ] JWT stored in localStorage
- [ ] Shop displays 5 slots horizontally (scroll)
- [ ] Board/Bench display with flex-wrap (no scroll)
- [ ] Synergies show tier colors (green/blue/purple/orange)
- [ ] Combat overlay opens on "Walcz" button
- [ ] HP bars update in real-time during combat
- [ ] Combat log shows attacks/deaths
- [ ] Gold/XP update after combat

### Discord Bot
- [ ] `/start` creates new player
- [ ] `/shop` shows 5 units
- [ ] `/combat` uses CombatSimulator
- [ ] Same gold/XP calculation as web

## Future Improvements

1. **WebSocket Combat** - dla better responsiveness
2. **Leaderboard** - ranking by wins/level
3. **Replays** - save combat data dla replay viewing
4. **Mobile UI** - responsive design dla mobile
5. **Animations** - smooth transitions dla unit moves
6. **Sound Effects** - combat sounds
7. **Tutorial** - onboarding dla new players
8. **More Units/Traits** - expand content
9. **PvP Mode** - real-time against online players
10. **Season System** - periodic resets z rewards

## For Future AI Assistants

**Key Points:**
1. **NIE duplikuj logiki** - zawsze używaj `waffen-tactics` core modules
2. **Combat.py jest shared** - zmiana musi działać dla Discord i Web
3. **Gold formula:** 5 base + min(5, gold//10) interest + 1 for win
4. **XP formula:** +2 always, level up when xp >= level*2
5. **Rarity colors:** based on unit cost (1-5)
6. **Tier colors:** based on synergy count (2/3/4/6+ → T1/T2/T3/T4)
7. **Shop jest horizontal** (overflow-x-auto), Board/Bench są flex-wrap
8. **Backend port 8000**, Frontend port 3000
9. **JWT w localStorage** dla authentication
10. **SSE dla combat streaming**, nie WebSocket

**When debugging:**
- Check backend logs (print statements w api.py)
- Check browser console dla frontend errors
- Verify JWT token exists w localStorage
- Check database connections (PostgreSQL)
- Ensure ports 8000 i 3000 są dostępne

**When adding features:**
- If game logic: modify `waffen-tactics` core
- If combat: modify shared `combat.py`
- If UI: modify frontend components
- If API: modify `api.py` endpoints
- Always test both Discord bot i web version

**Database migrations:**
```python
# Use DatabaseManager methods:
await db_manager.save_player_state(player)  # Save to user_states
await db_manager.get_player_state(user_id)  # Load from user_states
await db_manager.save_opponent_team(...)     # Save to opponent_teams
await db_manager.get_random_opponent(wins)   # Load from opponent_teams
```

Good luck! 🎮
