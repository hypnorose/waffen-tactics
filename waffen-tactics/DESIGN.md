# Waffen Tactics – Design Document v0.2

## Overview
Auto-battler game inspired by Teamfight Tactics, implemented as a Discord bot with interactive buttons and menus.
- Players build teams of 51 unique units with 14 traits (6 factions, 8 classes)
- Turn-less time-stepped combat simulation (dt=0.1s)
- Star upgrade system: 3× ⭐ → ⭐⭐, 3× ⭐⭐ → ⭐⭐⭐
- Persistent player state stored in SQLite
- Asynchronous PvP with stored team snapshots

## Core Data

### Units (units.json)
- **51 units** with `id`, `name`, `cost` (1-5), `factions[]`, `classes[]`
- Base stats scale by cost:
  - Attack: 40 + 12×cost
  - HP: 420 + 120×cost
  - Defense: 12 + 6×cost
  - Attack Speed: 0.7 + 0.06×cost
  - Max Mana: 100 (fixed)

### Traits (traits.json)
- **14 traits** with multi-tier activation thresholds
- Effect types: `stat_buff`, `on_enemy_death`, `on_ally_death`, `per_round_buff`, `enemy_debuff`, `hp_regen_on_kill`, `per_trait_buff`, `mana_regen`, `on_sell_bonus`, `stat_steal`
- Example: Srebrna Gwardia [3,5,7] → +15/25/40 defense

### Skills
- Generic skill: 60 + 25×cost damage, costs 100 mana
- Charges: +10 mana per attack
- Future: unique skills per class/faction

## Player Progression

### Resources
- **Gold**: Starting 10g, +5g per round
- **HP**: Starting 100, lose HP on defeat (survivors + round number)
- **Level**: 1-10, increases max board size (2→10)
- **XP**: Buy 4 XP for 4g, combat rewards XP

### Level Benefits
| Level | Max Units | Shop Odds (Cost 1/2/3/4/5) |
|-------|-----------|----------------------------|
| 1     | 2         | 100/0/0/0/0                |
| 5     | 6         | 50/30/15/4/1               |
| 10    | 10        | 5/20/35/25/15              |

## Shop Phase

### Mechanics
- **5 unit slots** refreshed each round
- **Reroll**: 2g for new offers (preserves duplicates correctly)
- **Buy**: Unit cost in gold, goes to bench (max 9)
- **Sell**: Refund = cost × star_level
- **Lock Shop**: Preserve offers for next round (not yet implemented)

### Auto-Upgrade System
When player acquires 3rd copy of same unit at same star level:
1. Remove 3 copies from bench/board
2. Create 1 unit at star_level + 1
3. Place on bench (or board if bench full)
4. Recursive: check for further upgrades

### UI Features
- Display unit stats: ⚔️ Attack, ❤️ HP, 🛡️ Defense
- Show factions and classes for each unit
- Upgrade hints: "(2/3 do ⭐⭐)"
- Shop footer with upgrade reminder

## Board Management

### Bench (max 9 units)
- Temporary storage for purchased units
- Move to board with "➡️ Na planszę" button
- Sell for gold with "💰 Sprzedaj" button
- Shows unit stats scaled by star level

### Board (max by level)
- Active combat units
- Remove to bench with "⬅️ Na ławkę" button
- Displays total team power (sum HP/Attack)
- Real-time synergy calculation

### Synergies Display
- Active traits with current tier
- Count progress: [current/next threshold]
- Example: "**Gamer** [5] - Tier 2 (następny: 7)"

## Combat Phase

### Simulation Mechanics
- **Time-stepped**: dt = 0.1s ticks, max 120s
- **Attack probability**: attack_speed × dt per tick
- **Target selection**: 60% prioritize highest defense, 40% random
- **Damage formula**: max(1, attack - defense)
- **Mana system**: +10 per attack, cast skill at 100
- **Victory**: All enemy units HP ≤ 0

### Combat Resolution
- **Win**: +0 damage, gold reward, streak++
- **Loss**: Damage = survivors + round_number, streak--
- **Game Over**: HP ≤ 0, use `/reset` to restart

### Opponents (Future)
- Stored team snapshots in database
- Matchmaking by wins/rounds
- AI-controlled during combat simulation

## Discord Bot Interface

### Commands
- `/graj` - Start/resume game (sends to DM)
- `/reset` - Reset progress
- `/profil` - View stats

### Interactive UI
Main menu buttons:
- 🏪 **Sklep** - Browse and buy units
- 📋 **Ławka** - Manage bench units
- ⚔️ **Plansza** - View board and synergies
- 🔄 **Reroll (2g)** - Refresh shop
- 📈 **Kup XP (4g)** - Buy 4 XP
- ⚔️ **Walcz!** - Start combat round

### Embed Information
**Game State Embed:**
- Resources: Gold, Level, XP bar
- Stats: W/L record, winrate, streak with emoji
- Units: Board/bench/total count
- Active synergies (up to 5 displayed)

**Shop Embed:**
- Unit name, cost, star level
- Stats: Attack/HP/Defense
- Factions and classes
- Action costs in description

**Bench/Board Embeds:**
- Unit stats scaled by star level
- Sell value
- Upgrade progress indicators
- Total team power on board

## Technical Architecture

### Backend Services
- **GameManager**: Handles all player actions (buy, sell, move, upgrade)
- **ShopService**: Generates offers based on level odds
- **SynergyEngine**: Computes active traits from team composition
- **CombatSimulator**: Time-stepped battle simulation
- **DatabaseManager**: SQLite persistence with async operations

### Data Models
- **PlayerState**: Complete game state (resources, units, progress)
- **UnitInstance**: Individual unit with star_level and instance_id
- **Unit**: Template from units.json with stats/skills
- **GameData**: Loaded units, traits, factions, classes

### File Structure
```
waffen-tactics/
├── src/waffen_tactics/
│   ├── models/
│   │   ├── unit.py
│   │   ├── player.py
│   │   └── player_state.py
│   ├── services/
│   │   ├── data_loader.py
│   │   ├── shop.py
│   │   ├── synergy.py
│   │   ├── combat.py
│   │   ├── game_manager.py
│   │   └── database.py
│   └── cli.py
├── tests/
│   ├── test_combat.py
│   ├── test_data_loader.py
│   └── test_traits.py
├── units.json (51 units)
├── traits.json (14 traits)
├── discord_bot.py (main bot)
├── .env (bot token)
└── waffen_tactics_game.db (player data)
```

## Current Status (v0.1)

### ✅ Implemented
- Discord bot with slash commands and DM support
- Full shop system with auto-upgrades
- Bench and board management
- 51 units with cost-based stats
- 14 traits with detailed effect definitions
- Time-stepped combat simulator
- SQLite persistence
- Interactive button UI with real-time updates
- Comprehensive unit tests (47 tests passing)

### 🚧 In Progress
- Trait effects application in combat (defined but not active)
- Unique skills per class/faction
- Enhanced UI with more statistics

### 📋 Planned
- Opponent matchmaking system
- Team snapshot storage
- Shop lock functionality
- Tournament mode
- Leaderboards
- Trait effect visual indicators
- Combat replay system
- Approved WFT-139 Set 2 item matrix is documented; runtime contract and canonical-source migration remain in WFT-140/WFT-141+
- Economy balancing
