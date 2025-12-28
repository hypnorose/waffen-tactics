# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**Waffen Tactics** is a web-based auto-battler game (similar to TFT) with a React frontend. The game features 51 unique units with faction/class synergies, star-based upgrades, and turn-based PvP combat.

### Architecture

**Primary Platform**: Web application (`waffen-tactics-web/`)
- React frontend + Flask backend
- Real-time combat streaming via SSE (Server-Sent Events)
- Animated combat with event-based synchronization

**Discord Integration** (`waffen-tactics/`):
- Helper commands only (e.g., `/ranking`)
- Game logic being migrated out of Discord
- Shares combat simulation engine with web backend

## Commands

### Core Game Logic & Tests (waffen-tactics/)

The `waffen-tactics/` directory contains shared game logic and tests. The Discord bot here is **being phased out** - gameplay happens on the web, Discord only provides helper commands.

```bash
# Run tests (primary use of this directory)
cd waffen-tactics
source bot_venv/bin/activate  # or create: python3 -m venv bot_venv
pip install -r bot_requirements.txt

python -m pytest tests/
python -m pytest tests/test_combat.py -v  # Single test file
python -m pytest tests/test_combat.py::test_specific_function -v  # Single test
python -m pytest -k "mana"  # Tests matching pattern

# Run Discord bot (helper commands only)
python discord_bot.py
```

### Web Backend (waffen-tactics-web/backend/)

```bash
# Development
cd waffen-tactics-web/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend API
python api.py  # Starts Flask on port 8000
```

### Web Frontend (waffen-tactics-web/)

```bash
# Development
cd waffen-tactics-web
npm install

# Run dev server
npm run dev  # Vite dev server on port 3000 or 5173

# Build for production
npm run build

# Lint
npm run lint
```

### Production Deployment

```bash
# Start all services
./start-all.sh

# Stop all services
./stop-all.sh

# Check status
./status.sh
```

## Architecture

### Core Combat System

The combat simulation engine is located in `waffen-tactics/src/waffen_tactics/services/` and imported by the web backend.

**Location**: `waffen-tactics/src/waffen_tactics/services/`

**Key Components**:
- `combat_simulator.py`: Tick-based simulation (0.1s per tick, 120s timeout)
- `combat_attack_processor.py`: Attack resolution, damage calculation
- `combat_effect_processor.py`: Buff/debuff/DoT handling
- `combat_regeneration_processor.py`: Mana and HP regeneration
- `event_canonicalizer.py`: Standardized event emission

**Combat Flow**:
1. Build teams from player/opponent units
2. Apply synergy buffs via `SynergyEngine`
3. Run tick-based simulation loop
4. Emit events via optional `event_callback`
5. Return result with winner, duration, survivors

### Event System Architecture

**Critical Design**: Combat events power real-time web UI synchronization.

**Event Flow**:
```
CombatSimulator.simulate(event_callback)
  → For each combat tick:
    → emit_attack(), emit_mana_update(), emit_stat_buff(), etc.
    → event_callback('attack', payload)
  → Every 1 second: emit_state_snapshot() with full unit states
```

**Event Properties**:
- `seq`: Sequence number (incremented per event, enables ordering)
- `event_id`: UUID (for idempotency/deduplication)
- `timestamp`: Simulation time in seconds
- `type`: Event type (attack, mana_update, stat_buff, etc.)

**State Snapshots**: Full game state emitted every second for frontend reconciliation. Contains authoritative HP, mana, effects for all units.

### Web SSE Streaming

**Backend Route**: `waffen-tactics-web/backend/routes/game_combat.py`

```
POST /game/combat
  → Prepare player/opponent units with synergies
  → Run CombatSimulator with event_callback
  → For each event: map_event_to_sse_payload()
  → Yield SSE: "data: {json}\n\n"
  → Finally: process_combat_results()
```

**Frontend Hook**: `waffen-tactics-web/src/hooks/combat/useCombatSSEBuffer.ts`

- Maintains global SSE connection (survives HMR)
- Buffers all events until `end` event received
- Triggers `isBufferedComplete` when ready

**Replay Loop**: `waffen-tactics-web/src/hooks/useCombatOverlayLogic.ts`

- Iterates buffered events in sequence
- Applies each via `applyCombatEvent()`
- Triggers animations (attack, skill cast, flash)
- Compares state with snapshots to detect desync
- Uses `replayTiming` to calculate delay between events

### Desync Detection

**Problem**: Frontend state may diverge from backend simulation due to event ordering, missing effects, or application bugs.

**Solution**:
- `CombatEventReconstructor` (backend): Replays events to validate state matches snapshots
- `compareCombatStates()` (frontend): Compares local state with snapshot `game_state`
- `DesyncInspector` component: Shows detected differences for debugging

See `docs/DESYNC_IMPROVEMENTS.md` for detailed mitigation strategies.

### Database Schema

**Primary Database**: `waffen-tactics-web/backend/game_data.db` (SQLite)

**Tables**:
- `players`: Player state (units, gold, level, HP, shop, etc.) as JSON blob
- `opponent_teams`: Cached opponent teams for matchmaking
- `leaderboard`: High scores (also used by Discord ranking commands)

**Legacy**: `waffen-tactics/waffen_tactics_game.db` exists for Discord bot helper commands (read-only access to leaderboard).

**Important**: `GameManager.load_game_data()` loads units/traits/skills from JSON files at startup. Changes to `units.json` or `traits.json` require web backend restart.

### Shared Code

Web backend imports core game logic from `waffen-tactics/src/waffen_tactics/`:

- **Combat**: `CombatSimulator`, `CombatManager`, processors
- **Game Logic**: `GameManager`, `SynergyEngine`, `StatCalculator`
- **Data**: `DataLoader` (loads units.json, traits.json, skills.json)
- **Database**: `DatabaseManager` (player persistence)
- **Models**: `PlayerState`, `CombatUnit`, `Skill`

**Web-specific** services in `waffen-tactics-web/backend/services/`:
- `combat_service.py`: Unit preparation, result processing
- `combat_event_reconstructor.py`: Event replay validation

**Discord bot**: Only uses `DatabaseManager` for leaderboard queries (helper commands).

### Data Files

**Location**: `waffen-tactics/`

- `units.json`: 51 unit definitions (stats, costs, factions, classes, skills)
- `traits.json`: Faction/class synergies with tier thresholds
- `skills.json`: Unit abilities with damage/buff/heal effects
- `unit_roles.json`: Role classifications (tank, damage, support)

**Validation**: Run `validate_units.py` after editing JSON files.

## Key Patterns

### HP Tracking Separation

Combat simulator maintains separate `a_hp` and `b_hp` lists instead of mutating unit objects. This enables:
- Authoritative HP in event payloads
- Consistent replay without stat mutation
- Easy snapshot generation

### Effect ID Tracking

Each buff/debuff/DoT has a UUID `effect_id`:
- Enables deterministic expiration
- Allows precise removal in events
- DoT effects track `effect_id` for cleanup

### Mana Delta Calculation

Simulator tracks `_last_mana` per unit to compute deltas:
- `mana_update` events include both `current_mana` and `amount` (delta)
- Ensures frontend can apply incremental or absolute updates

### Snapshot-Based Validation

State snapshots emitted every second serve as reconciliation points:
- Frontend validates against snapshots
- Backend reconstructor detects divergence
- Allows detection of event application bugs

### Event Canonicalization

All events pass through canonical emitters in `event_canonicalizer.py`:
- Standardizes field names (`amount`, `value_type`, `duration`)
- Guarantees required fields (`seq`, `event_id`, `timestamp`)
- Mutates server state before returning payload (authoritative)

## Testing

### Backend Tests

**Location**: `waffen-tactics/tests/`

**Key Test Files**:
- `test_combat.py`: Basic combat simulation
- `test_comprehensive_system.py`: Full game flow
- `test_event_canonicalizer.py`: Event shape validation
- `test_replay_validation.py`: Event replay consistency
- `test_effects_events.py`: Buff/debuff event correctness
- `test_mana_regeneration.py`: Mana system

**Run specific scenarios**:
```bash
# Replay a specific combat seed
python -m pytest tests/test_replay_seed_*.py -v

# Test with combat logging
python tmp_debug_seed5.py
```

### Web Backend Tests

**Location**: `waffen-tactics-web/backend/tests/`

```bash
cd waffen-tactics-web/backend
python -m pytest tests/ -v
```

## Common Tasks

### Add a New Unit

1. Edit `waffen-tactics/units.json`:
   - Add unit definition with `id`, `name`, `cost`, `base_stats`, `factions`, `classes`, `skills`
2. Validate: `python validate_units.py`
3. Restart backend/bot (GameManager caches on load)

### Add a New Skill

1. Edit `waffen-tactics/skills.json`: Define skill effects
2. Implement handler in `skill_executor.py` if needed
3. Add event emission for skill effects
4. Test with `python -m pytest tests/test_skill_effect_events.py`

### Add a New Trait

1. Edit `waffen-tactics/traits.json`: Define faction/class synergy
2. Update `synergy.py` if custom logic needed
3. Test synergy application with `python test_buffed_stats.py`

### Debug Combat Desync

1. Check `DesyncInspector` component in web UI
2. Review backend logs for `CombatEventReconstructor` diffs
3. Capture event stream: Combat overlay saves events to browser console
4. Replay locally: Save events to `*.jsonl` and test with reconstructor
5. See `docs/DESYNC_IMPROVEMENTS.md` for systematic debugging

### Update Frontend Combat Animation

1. Modify `waffen-tactics-web/src/hooks/combat/useCombatAnimations.ts`
2. Adjust timing in `replayTiming.ts`
3. Update event handlers in `applyEvent.ts`

## Project Structure

```
waffen-tactics-game/
├── waffen-tactics/                      # Shared game logic + tests
│   ├── src/waffen_tactics/
│   │   ├── services/
│   │   │   ├── combat_simulator.py      # Core simulation engine
│   │   │   ├── combat_manager.py        # Combat orchestration
│   │   │   ├── event_canonicalizer.py   # Event standardization
│   │   │   ├── skill_executor.py        # Skill resolution
│   │   │   ├── synergy.py               # Trait calculation
│   │   │   ├── database.py              # SQLite persistence
│   │   │   └── game_manager.py          # Main game controller
│   │   └── models/                      # Data models
│   ├── tests/                           # Combat & game logic tests
│   ├── units.json                       # Unit definitions (source of truth)
│   ├── traits.json                      # Synergy definitions (source of truth)
│   ├── skills.json                      # Skill definitions (source of truth)
│   └── discord_bot.py                   # Discord bot (helper commands only)
│
├── waffen-tactics-web/                  # Web application (PRIMARY PLATFORM)
│   ├── backend/
│   │   ├── routes/
│   │   │   ├── game_routes.py           # Game state management
│   │   │   └── game_combat.py           # SSE combat streaming
│   │   ├── services/
│   │   │   ├── combat_service.py        # Unit prep, result processing
│   │   │   └── combat_event_reconstructor.py  # Event validation
│   │   ├── api.py                       # Flask app entry point
│   │   └── game_data.db                 # Primary database
│   ├── src/
│   │   ├── components/                  # React components
│   │   │   ├── CombatOverlay.tsx        # Combat UI
│   │   │   ├── GameBoard.tsx            # Unit board
│   │   │   ├── Shop.tsx                 # Unit shop
│   │   │   └── DesyncInspector.tsx      # Desync debugging
│   │   ├── hooks/
│   │   │   ├── useCombatOverlayLogic.ts # Replay loop
│   │   │   └── combat/
│   │   │       ├── useCombatSSEBuffer.ts    # SSE connection
│   │   │       ├── applyEvent.ts            # Event handlers
│   │   │       ├── useCombatAnimations.ts   # Animation system
│   │   │       └── desync.ts                # State comparison
│   │   └── pages/
│   │       └── Game.tsx                 # Main game page
│   └── package.json
│
├── docs/
│   ├── DESYNC_IMPROVEMENTS.md           # Desync mitigation guide
│   └── DESYNC_MITIGATION_PLAN.md
│
└── scripts/                             # Utility scripts
```

## Important Notes

### State Management

- **Web backend**: Stateless Flask API, loads player state from SQLite per request
- **Web frontend**: Zustand store for game state, SSE buffer for combat events
- **Discord bot**: Read-only access to leaderboard for `/ranking` command

### Combat is Deterministic

Given the same team compositions and RNG seed, combat always produces identical results. This enables:
- Replay validation
- Desync detection via snapshot comparison
- Reproducible test scenarios

### Event Ordering Critical

Events must be applied in `seq` order on frontend. Out-of-order application causes desync. The SSE buffer ensures sequential delivery.

### Persistent Buffs

Units can have buffs that persist across rounds (e.g., Streamer trait: +stats per kill). Stored in `PlayerState` and applied before each combat.

### Star System

- 1-star: 100% base stats
- 2-star: 200% base stats (auto-upgrade from 3x 1-star)
- 3-star: 300% base stats (auto-upgrade from 3x 2-star)

Implemented via `star_scaling` multiplier in stat calculation.

### Frontend HMR Considerations

SSE connection uses global state to survive Hot Module Replacement. Check `useCombatSSEBuffer.ts` for implementation.

## Development Workflow

1. **Make changes** to game logic in `waffen-tactics/src/waffen_tactics/`
2. **Test** with pytest: `cd waffen-tactics && python -m pytest tests/`
3. **Restart** web backend: `cd waffen-tactics-web/backend && python api.py`
4. Frontend auto-reloads via Vite HMR (no restart needed)

For combat changes, always verify:
- Events are emitted via canonical emitters
- Events include `seq` and `event_id`
- State snapshots reflect post-event state
- Frontend replay produces correct visuals
- No desyncs detected in `DesyncInspector`

### Discord Bot Changes

The Discord bot is **legacy** and being phased out for gameplay. Only maintain helper commands:
- `/ranking` - Leaderboard display
- Other read-only commands as needed
- Do NOT add new gameplay features to Discord
