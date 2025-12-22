# ELO Rating System Implementation Plan

## Executive Summary

This document outlines a comprehensive plan for implementing an ELO rating system in Waffen Tactics. The current ranking system uses raw win counts, which doesn't account for opponent skill or match difficulty. An ELO system will provide:

- **Skill-based matchmaking** - Players face opponents of similar skill level
- **Fair ranking** - Better players naturally rise regardless of total games played
- **Match quality** - More competitive, balanced games
- **Progression tracking** - Clear skill improvement metrics

---

## Current System Analysis

### How Matchmaking Works Today

**Opponent Selection** (`database.py:244-356`):
1. **New players (≤5 rounds)**: Always face system bots (user_id ≤ 100000)
2. **Experienced players (>5 rounds)**: Matched by **total rounds played**
   - Tries ±1 round difference first
   - Falls back to ±3, then ±5
   - Falls back to system bots if no matches

**Issues**:
- Round count ≠ skill level (player could have 50% win rate at round 20)
- No consideration of opponent strength
- New skilled players crush beginners at same round count
- Lucky early winners dominate leaderboard

### Current Combat Result Processing

**Win** (`game_combat.py:568-602`):
```python
player.wins += 1
player.gold += 1
player.streak += 1
player.xp += 2
```

**Loss**:
```python
player.hp -= surviving_enemy_stars
player.losses += 1
player.streak = 0

if player.hp <= 0:
    # Game over - save to leaderboard
    save_to_leaderboard(wins, losses, level, round_number)
```

**Leaderboard Ranking**:
```sql
ORDER BY wins DESC, round_number DESC
```

**Issues**:
- Only total wins matter, not win rate
- No opponent difficulty weighting
- Players who quit early with good win rate don't rank
- System bots give free wins

---

## ELO System Design

### What is ELO?

ELO is a rating system that:
- Starts everyone at a base rating (1200 by default)
- Increases rating when you win, decreases when you lose
- **Beating stronger opponents** gives more rating gain
- **Losing to weaker opponents** loses more rating
- Converges to your true skill level over time

### Core Formula

```
Expected_Score = 1 / (1 + 10^((Opponent_ELO - Player_ELO) / 400))

New_Rating = Old_Rating + K * (Actual_Score - Expected_Score)
```

Where:
- `Actual_Score` = 1 (win), 0 (loss), 0.5 (draw)
- `K` = K-factor (how much rating changes per game)

**Example**:
- Player (1200) vs Opponent (1400)
- Expected score = 1 / (1 + 10^((1400-1200)/400)) = 0.24 (24% chance to win)
- If player WINS: New_Rating = 1200 + 32 * (1 - 0.24) = **1224** (+24)
- If player LOSES: New_Rating = 1200 + 32 * (0 - 0.24) = **1192** (-8)

**Key insight**: Beating a stronger opponent (+200 ELO) gives +24, while losing only costs -8!

---

## Implementation Plan

### Phase 1: Database Schema Updates

**1.1 Add ELO Fields to PlayerState**

**File**: `waffen-tactics/src/waffen_tactics/models/player_state.py`

```python
@dataclass
class PlayerState:
    # ... existing fields ...

    # ELO Rating System
    elo_rating: float = 1200.0          # Current ELO rating
    peak_elo: float = 1200.0            # Highest ELO ever achieved
    elo_games_played: int = 0           # Games counted for ELO (excludes bot games)
    provisional: bool = True            # True until 10 ranked games played
```

**1.2 Database Migration**

**File**: `waffen-tactics-web/backend/migrations/add_elo_fields.py` (NEW)

```python
import sqlite3

def migrate_add_elo_fields():
    """Add ELO rating fields to existing databases."""

    # Update players table (JSON field, no schema change needed)
    # PlayerState already serializes new fields automatically

    # Update opponent_teams table
    db_path = '/home/ubuntu/waffen-tactics-game/waffen-tactics/waffen_tactics_game.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add ELO column to opponent_teams
        cursor.execute('''
            ALTER TABLE opponent_teams
            ADD COLUMN elo_rating REAL DEFAULT 1200.0
        ''')

        # Add peak ELO column to leaderboard
        cursor.execute('''
            ALTER TABLE leaderboard
            ADD COLUMN peak_elo REAL DEFAULT 1200.0
        ''')

        cursor.execute('''
            ALTER TABLE leaderboard
            ADD COLUMN final_elo REAL DEFAULT 1200.0
        ''')

        conn.commit()
        print("✅ Database migration completed successfully")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Columns already exist, skipping migration")
        else:
            raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_add_elo_fields()
```

**1.3 Update Database Manager**

**File**: `waffen-tactics/src/waffen_tactics/services/database.py`

Add ELO to opponent team saves:

```python
def save_opponent_team(self, user_id, nickname, board_units, bench_units,
                       wins, losses, level, elo_rating=1200.0, avatar=None):
    """Save current team composition for matchmaking pool."""
    # ... existing code ...

    cursor.execute('''
        INSERT OR REPLACE INTO opponent_teams
        (user_id, nickname, team_json, wins, losses, level, elo_rating, avatar,
         is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
    ''', (user_id, nickname, team_json, wins, losses, level, elo_rating, avatar))
```

Update leaderboard saves:

```python
def save_to_leaderboard(self, user_id, nickname, wins, losses, level,
                        round_number, team_units, peak_elo=1200.0, final_elo=1200.0):
    """Save final game result to leaderboard."""
    # ... existing code ...

    cursor.execute('''
        INSERT INTO leaderboard
        (user_id, nickname, wins, losses, level, round_number, team_json,
         peak_elo, final_elo, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, nickname, wins, losses, level, round_number,
          team_json, peak_elo, final_elo))
```

---

### Phase 2: ELO Calculation Engine

**File**: `waffen-tactics-web/backend/services/elo_calculator.py` (NEW)

```python
"""
ELO Rating Calculation System for Waffen Tactics

Based on standard ELO with adjustments for:
- Provisional ratings (first 10 games)
- System bot matches (no ELO change)
- Dynamic K-factor based on rating volatility
"""

import math
from typing import Tuple

# Constants
BASE_ELO = 1200.0
PROVISIONAL_GAMES = 10
K_FACTOR_PROVISIONAL = 40  # High volatility for new players
K_FACTOR_NORMAL = 24       # Standard for established players
K_FACTOR_HIGH_RATED = 16   # Lower for high-rated players (>2000)


def calculate_expected_score(player_elo: float, opponent_elo: float) -> float:
    """
    Calculate expected win probability using ELO formula.

    Returns value between 0 and 1:
    - 0.5 = even match
    - 0.76 = player is +200 ELO stronger
    - 0.24 = player is -200 ELO weaker
    """
    return 1.0 / (1.0 + math.pow(10, (opponent_elo - player_elo) / 400.0))


def get_k_factor(player_elo: float, games_played: int, provisional: bool) -> int:
    """
    Determine K-factor (rating change multiplier) based on player state.

    Higher K-factor = more volatile rating changes
    - Provisional players: 40 (still finding true rating)
    - Normal players: 24 (standard)
    - High-rated players (>2000): 16 (more stable)
    """
    if provisional or games_played < PROVISIONAL_GAMES:
        return K_FACTOR_PROVISIONAL

    if player_elo >= 2000:
        return K_FACTOR_HIGH_RATED

    return K_FACTOR_NORMAL


def calculate_elo_change(
    player_elo: float,
    opponent_elo: float,
    player_won: bool,
    player_games_played: int,
    player_provisional: bool,
    is_bot_match: bool = False
) -> Tuple[float, dict]:
    """
    Calculate new ELO rating after a match.

    Args:
        player_elo: Current player ELO rating
        opponent_elo: Opponent's ELO rating
        player_won: True if player won, False if lost
        player_games_played: Number of ranked games played
        player_provisional: Whether player is still provisional
        is_bot_match: True if opponent is a system bot

    Returns:
        (new_elo, metadata_dict)

    metadata_dict contains:
        - old_elo: Starting ELO
        - new_elo: Ending ELO
        - elo_change: Delta (can be negative)
        - expected_score: Win probability (0-1)
        - k_factor: K-factor used
        - is_ranked: Whether this match affected ELO
    """
    # System bot matches don't affect ELO
    if is_bot_match:
        return player_elo, {
            'old_elo': player_elo,
            'new_elo': player_elo,
            'elo_change': 0.0,
            'expected_score': 0.0,
            'k_factor': 0,
            'is_ranked': False,
            'reason': 'Bot match - no ELO change'
        }

    # Calculate expected outcome
    expected_score = calculate_expected_score(player_elo, opponent_elo)

    # Actual score: 1 for win, 0 for loss, 0.5 for draw (not currently used)
    actual_score = 1.0 if player_won else 0.0

    # Get K-factor based on player state
    k_factor = get_k_factor(player_elo, player_games_played, player_provisional)

    # Calculate rating change
    elo_change = k_factor * (actual_score - expected_score)
    new_elo = player_elo + elo_change

    # Floor at 100 to prevent negative ratings
    new_elo = max(100.0, new_elo)

    return new_elo, {
        'old_elo': player_elo,
        'new_elo': new_elo,
        'elo_change': elo_change,
        'expected_score': expected_score,
        'k_factor': k_factor,
        'is_ranked': True,
        'opponent_elo': opponent_elo
    }


def get_elo_tier(elo: float) -> str:
    """
    Map ELO rating to tier name for display.

    Tier thresholds:
    - Bronze: < 1000
    - Silver: 1000-1199
    - Gold: 1200-1399 (starting tier)
    - Platinum: 1400-1599
    - Diamond: 1600-1799
    - Master: 1800-1999
    - Grandmaster: 2000+
    """
    if elo < 1000:
        return "Bronze"
    elif elo < 1200:
        return "Silver"
    elif elo < 1400:
        return "Gold"
    elif elo < 1600:
        return "Platinum"
    elif elo < 1800:
        return "Diamond"
    elif elo < 2000:
        return "Master"
    else:
        return "Grandmaster"


# Example usage and testing
if __name__ == '__main__':
    print("ELO Calculator Test Cases\n" + "="*50)

    # Test 1: Even match (1200 vs 1200)
    new_elo, meta = calculate_elo_change(1200, 1200, True, 5, True, False)
    print(f"\nTest 1: Even match (1200 vs 1200) - WIN")
    print(f"  Old: {meta['old_elo']:.1f}")
    print(f"  New: {meta['new_elo']:.1f}")
    print(f"  Change: {meta['elo_change']:+.1f}")
    print(f"  Expected: {meta['expected_score']:.1%}")

    # Test 2: Underdog win (1200 vs 1400)
    new_elo, meta = calculate_elo_change(1200, 1400, True, 5, True, False)
    print(f"\nTest 2: Underdog win (1200 vs 1400) - WIN")
    print(f"  Old: {meta['old_elo']:.1f}")
    print(f"  New: {meta['new_elo']:.1f}")
    print(f"  Change: {meta['elo_change']:+.1f}")
    print(f"  Expected: {meta['expected_score']:.1%}")

    # Test 3: Underdog loss (1200 vs 1400)
    new_elo, meta = calculate_elo_change(1200, 1400, False, 5, True, False)
    print(f"\nTest 3: Underdog loss (1200 vs 1400) - LOSS")
    print(f"  Old: {meta['old_elo']:.1f}")
    print(f"  New: {meta['new_elo']:.1f}")
    print(f"  Change: {meta['elo_change']:+.1f}")
    print(f"  Expected: {meta['expected_score']:.1%}")

    # Test 4: Bot match
    new_elo, meta = calculate_elo_change(1200, 1200, True, 5, True, True)
    print(f"\nTest 4: Bot match - WIN (no ELO change)")
    print(f"  Old: {meta['old_elo']:.1f}")
    print(f"  New: {meta['new_elo']:.1f}")
    print(f"  Change: {meta['elo_change']:+.1f}")
    print(f"  Reason: {meta['reason']}")

    # Test 5: Established player (lower K-factor)
    new_elo, meta = calculate_elo_change(1500, 1500, True, 50, False, False)
    print(f"\nTest 5: Established player (K={meta['k_factor']}) - WIN")
    print(f"  Old: {meta['old_elo']:.1f}")
    print(f"  New: {meta['new_elo']:.1f}")
    print(f"  Change: {meta['elo_change']:+.1f}")
```

---

### Phase 3: Integration into Combat Flow

**File**: `waffen-tactics-web/backend/routes/game_combat.py`

**3.1 Import ELO Calculator**

```python
from ..services.elo_calculator import calculate_elo_change, get_elo_tier
```

**3.2 Fetch Opponent ELO Before Combat**

Modify around line 290-320:

```python
# Get opponent
if player.round_number <= 5:
    opponent_data = run_async(db_manager.get_random_system_opponent())
    is_bot_match = True
    opponent_elo = 1200.0  # Bots have default ELO
else:
    opponent_data = run_async(db_manager.get_random_opponent(
        current_round=player.wins + player.losses,
        user_id=user_id
    ))
    if not opponent_data:
        opponent_data = run_async(db_manager.get_random_system_opponent())
        is_bot_match = True
        opponent_elo = 1200.0
    else:
        is_bot_match = opponent_data['user_id'] <= 100000
        opponent_elo = opponent_data.get('elo_rating', 1200.0)

# Store for ELO calculation later
combat_metadata = {
    'opponent_elo': opponent_elo,
    'is_bot_match': is_bot_match
}
```

**3.3 Calculate ELO After Combat**

Modify around line 568-602:

```python
# Determine winner
if result['winner'] == 'team_a':  # Player wins
    player_won = True
    player.wins += 1
    player.gold += 1
    player.streak += 1
    player.xp += 2
    victory_message = "🎉 Zwycięstwo!"

elif result['winner'] == 'team_b':  # Player loses
    player_won = False
    hp_loss = result.get('surviving_star_sum', 0)
    player.hp -= hp_loss
    player.losses += 1
    player.streak = 0
    victory_message = None

# CRITICAL: Calculate ELO rating change
new_elo, elo_metadata = calculate_elo_change(
    player_elo=player.elo_rating,
    opponent_elo=combat_metadata['opponent_elo'],
    player_won=player_won,
    player_games_played=player.elo_games_played,
    player_provisional=player.provisional,
    is_bot_match=combat_metadata['is_bot_match']
)

# Update player ELO
old_elo = player.elo_rating
player.elo_rating = new_elo

if elo_metadata['is_ranked']:
    player.elo_games_played += 1

    # Update provisional status
    if player.elo_games_played >= 10:
        player.provisional = False

    # Track peak ELO
    if new_elo > player.peak_elo:
        player.peak_elo = new_elo

# Log ELO change for debugging
print(f"[ELO] {username}: {old_elo:.1f} → {new_elo:.1f} "
      f"({elo_metadata['elo_change']:+.1f}) vs {combat_metadata['opponent_elo']:.1f}")
```

**3.4 Save ELO to Opponent Team**

Modify around line 648-660:

```python
# Save current team to opponent pool
run_async(db_manager.save_opponent_team(
    user_id=user_id,
    nickname=username,
    board_units=board_units,
    bench_units=bench_units,
    wins=player.wins,
    losses=player.losses,
    level=player.level,
    elo_rating=player.elo_rating,  # ADD THIS
    avatar=player_avatar
))
```

**3.5 Save ELO to Leaderboard on Game Over**

Modify around line 590-602:

```python
if player.hp <= 0:
    # Game over - save to leaderboard
    run_async(db_manager.save_to_leaderboard(
        user_id=user_id,
        nickname=username,
        wins=player.wins,
        losses=player.losses,
        level=player.level,
        round_number=player.round_number,
        team_units=team_units,
        peak_elo=player.peak_elo,     # ADD THIS
        final_elo=player.elo_rating   # ADD THIS
    ))
```

**3.6 Return ELO Data in Combat Events**

Add to final event emission:

```python
# After combat ends, send ELO change event
if elo_metadata['is_ranked']:
    elo_event = {
        'type': 'elo_update',
        'old_elo': elo_metadata['old_elo'],
        'new_elo': elo_metadata['new_elo'],
        'elo_change': elo_metadata['elo_change'],
        'opponent_elo': elo_metadata['opponent_elo'],
        'tier': get_elo_tier(elo_metadata['new_elo']),
        'provisional': player.provisional,
        'games_played': player.elo_games_played
    }
    yield f"data: {json.dumps(elo_event)}\n\n"
```

---

### Phase 4: ELO-Based Matchmaking

**File**: `waffen-tactics/src/waffen_tactics/services/database.py`

**4.1 Add ELO-Based Opponent Search**

Replace `get_random_opponent()` (lines 244-356):

```python
def get_random_opponent(self, current_round: int, user_id: int, player_elo: float = 1200.0):
    """
    Find opponent using ELO-based matchmaking with fallback to round-based.

    Search strategy:
    1. Try ELO window ±100 points (closest skill match)
    2. Try ELO window ±200 points
    3. Try ELO window ±400 points
    4. Fall back to round-based matching (±3 rounds)
    5. Fall back to system bots

    Within each window, prioritizes closer ELO matches.
    """
    cursor = self.conn.cursor()

    # ELO-based search windows (in order of preference)
    elo_windows = [100, 200, 400]

    for window in elo_windows:
        cursor.execute('''
            SELECT user_id, nickname, team_json, wins, losses, level,
                   elo_rating, avatar, avatar_local
            FROM opponent_teams
            WHERE user_id > 100000
              AND is_active = 1
              AND user_id != ?
              AND ABS(elo_rating - ?) <= ?
            ORDER BY ABS(elo_rating - ?), RANDOM()
            LIMIT 1
        ''', (user_id, player_elo, window, player_elo))

        row = cursor.fetchone()
        if row:
            print(f"[MATCHMAKING] Found opponent within ELO ±{window}: "
                  f"Player={player_elo:.0f}, Opponent={row[6]:.0f}")
            return {
                'user_id': row[0],
                'nickname': row[1],
                'board': json.loads(row[2]).get('board', []),
                'bench': json.loads(row[2]).get('bench', []),
                'wins': row[3],
                'losses': row[4],
                'level': row[5],
                'elo_rating': row[6],
                'avatar': row[7] or row[8]
            }

    # Fall back to round-based matching if no ELO matches
    print(f"[MATCHMAKING] No ELO match found, falling back to round-based")
    round_windows = [1, 3, 5]

    for window in round_windows:
        cursor.execute('''
            SELECT user_id, nickname, team_json, wins, losses, level,
                   elo_rating, avatar, avatar_local
            FROM opponent_teams
            WHERE user_id > 100000
              AND is_active = 1
              AND user_id != ?
              AND ABS((wins + losses) - ?) <= ?
            ORDER BY RANDOM()
            LIMIT 1
        ''', (user_id, current_round, window))

        row = cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'nickname': row[1],
                'board': json.loads(row[2]).get('board', []),
                'bench': json.loads(row[2]).get('bench', []),
                'wins': row[3],
                'losses': row[4],
                'level': row[5],
                'elo_rating': row[6],
                'avatar': row[7] or row[8]
            }

    # Final fallback to system bots
    print(f"[MATCHMAKING] No player matches, using system bot")
    return None  # Caller will use get_random_system_opponent()
```

**4.2 Update Combat Service to Pass ELO**

**File**: `waffen-tactics-web/backend/services/combat_service.py`

```python
# Around line 290-320
opponent_data = run_async(db_manager.get_random_opponent(
    current_round=player.wins + player.losses,
    user_id=user_id,
    player_elo=player.elo_rating  # ADD THIS
))
```

---

### Phase 5: Leaderboard Updates

**File**: `waffen-tactics/src/waffen_tactics/services/database.py`

**5.1 Update Leaderboard Query**

Modify `get_leaderboard()` (lines 160-187):

```python
def get_leaderboard(self, period='all', limit=10):
    """
    Retrieve top players by peak ELO rating.

    Primary ranking: peak_elo (highest rating ever achieved)
    Secondary: final_elo (rating at game end)
    Tertiary: wins
    """
    cursor = self.conn.cursor()

    if period == '24h':
        cursor.execute('''
            SELECT user_id, nickname, wins, losses, level, round_number,
                   peak_elo, final_elo, created_at
            FROM leaderboard
            WHERE created_at >= datetime('now', '-1 day')
            ORDER BY peak_elo DESC, final_elo DESC, wins DESC
            LIMIT ?
        ''', (limit,))
    else:  # 'all'
        cursor.execute('''
            SELECT user_id, nickname, wins, losses, level, round_number,
                   peak_elo, final_elo, created_at
            FROM leaderboard
            ORDER BY peak_elo DESC, final_elo DESC, wins DESC
            LIMIT ?
        ''', (limit,))

    rows = cursor.fetchall()

    leaderboard = []
    for row in rows:
        leaderboard.append({
            'user_id': row[0],
            'nickname': row[1],
            'wins': row[2],
            'losses': row[3],
            'win_rate': f"{row[2] / (row[2] + row[3]) * 100:.1f}%" if (row[2] + row[3]) > 0 else "0%",
            'level': row[4],
            'rounds': row[5],
            'peak_elo': row[6],
            'final_elo': row[7],
            'tier': get_elo_tier(row[6]),
            'created_at': row[8]
        })

    return leaderboard
```

**5.2 Add Live Leaderboard (Active Players)**

```python
def get_live_leaderboard(self, limit=10):
    """
    Get leaderboard of currently active players (not game-overed).

    Uses current ELO from opponent_teams table.
    """
    cursor = self.conn.cursor()

    cursor.execute('''
        SELECT user_id, nickname, wins, losses, level, elo_rating, avatar
        FROM opponent_teams
        WHERE is_active = 1
          AND user_id > 100000
        ORDER BY elo_rating DESC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()

    leaderboard = []
    for row in rows:
        leaderboard.append({
            'user_id': row[0],
            'nickname': row[1],
            'wins': row[2],
            'losses': row[3],
            'win_rate': f"{row[2] / (row[2] + row[3]) * 100:.1f}%" if (row[2] + row[3]) > 0 else "0%",
            'level': row[4],
            'elo_rating': row[5],
            'tier': get_elo_tier(row[5]),
            'avatar': row[6]
        })

    return leaderboard
```

---

### Phase 6: Frontend UI Updates

**6.1 Combat Result ELO Display**

**File**: `waffen-tactics-web/src/components/CombatOverlay.tsx`

Add ELO change notification after combat ends:

```tsx
{combatState.isFinished && eloUpdate && (
  <div className="elo-update-notification">
    <div className="elo-change-header">
      {eloUpdate.provisional && <span className="provisional-badge">Provisional</span>}
      <span className="tier-badge">{eloUpdate.tier}</span>
    </div>

    <div className="elo-change-display">
      <span className="old-elo">{Math.round(eloUpdate.old_elo)}</span>
      <span className={`elo-delta ${eloUpdate.elo_change >= 0 ? 'positive' : 'negative'}`}>
        {eloUpdate.elo_change >= 0 ? '+' : ''}{Math.round(eloUpdate.elo_change)}
      </span>
      <span className="new-elo">{Math.round(eloUpdate.new_elo)}</span>
    </div>

    <div className="opponent-elo-info">
      vs {Math.round(eloUpdate.opponent_elo)} ELO
    </div>

    {eloUpdate.provisional && (
      <div className="provisional-info">
        {eloUpdate.games_played}/10 placement matches
      </div>
    )}
  </div>
)}
```

**6.2 Leaderboard ELO Display**

**File**: `waffen-tactics-web/src/components/Leaderboard.tsx`

Update leaderboard table to show ELO:

```tsx
<table className="leaderboard-table">
  <thead>
    <tr>
      <th>Rank</th>
      <th>Player</th>
      <th>ELO</th>
      <th>Tier</th>
      <th>W/L</th>
      <th>Win Rate</th>
      <th>Level</th>
    </tr>
  </thead>
  <tbody>
    {leaderboard.map((entry, index) => (
      <tr key={entry.user_id}>
        <td>{index + 1}</td>
        <td>{entry.nickname}</td>
        <td className="elo-rating">{Math.round(entry.peak_elo)}</td>
        <td className={`tier-badge tier-${entry.tier.toLowerCase()}`}>
          {entry.tier}
        </td>
        <td>{entry.wins}W / {entry.losses}L</td>
        <td>{entry.win_rate}</td>
        <td>{entry.level}</td>
      </tr>
    ))}
  </tbody>
</table>
```

**6.3 Opponent Preview ELO**

**File**: `waffen-tactics-web/src/components/OpponentPreview.tsx`

Show opponent ELO before battle:

```tsx
<div className="opponent-preview">
  <div className="opponent-header">
    <h3>{opponentInfo.nickname}</h3>
    <div className="opponent-stats">
      <span className="elo-badge">{Math.round(opponentInfo.elo_rating)} ELO</span>
      <span className="tier-badge">{opponentInfo.tier}</span>
    </div>
  </div>

  <div className="opponent-record">
    {opponentInfo.wins}W - {opponentInfo.losses}L
    ({opponentInfo.win_rate})
  </div>

  {/* Expected win probability */}
  <div className="match-odds">
    Your win chance: {Math.round(expectedScore * 100)}%
  </div>
</div>
```

---

## Testing Plan

### Unit Tests

**File**: `waffen-tactics-web/backend/tests/test_elo_calculator.py` (NEW)

```python
import pytest
from services.elo_calculator import (
    calculate_expected_score,
    calculate_elo_change,
    get_k_factor,
    get_elo_tier
)

def test_expected_score_even_match():
    """Even match should have 50% expected score."""
    expected = calculate_expected_score(1200, 1200)
    assert abs(expected - 0.5) < 0.01

def test_expected_score_underdog():
    """Player 200 ELO lower should have ~24% win chance."""
    expected = calculate_expected_score(1200, 1400)
    assert abs(expected - 0.24) < 0.02

def test_elo_change_win_even_match():
    """Win in even match should gain ~20 ELO (K=40)."""
    new_elo, meta = calculate_elo_change(1200, 1200, True, 5, True, False)
    assert 1218 <= new_elo <= 1222  # ~20 gain

def test_elo_change_underdog_win():
    """Underdog win should gain more ELO."""
    new_elo, meta = calculate_elo_change(1200, 1400, True, 5, True, False)
    assert new_elo >= 1230  # Significant gain

def test_elo_change_underdog_loss():
    """Underdog loss should lose less ELO."""
    new_elo, meta = calculate_elo_change(1200, 1400, False, 5, True, False)
    assert 1190 <= new_elo <= 1194  # Small loss

def test_bot_match_no_change():
    """Bot matches should not affect ELO."""
    new_elo, meta = calculate_elo_change(1200, 1200, True, 5, True, True)
    assert new_elo == 1200
    assert meta['elo_change'] == 0.0
    assert not meta['is_ranked']

def test_k_factor_provisional():
    """Provisional players should have high K-factor."""
    k = get_k_factor(1200, 5, True)
    assert k == 40

def test_k_factor_normal():
    """Normal players should have standard K-factor."""
    k = get_k_factor(1200, 20, False)
    assert k == 24

def test_k_factor_high_rated():
    """High-rated players should have lower K-factor."""
    k = get_k_factor(2100, 100, False)
    assert k == 16

def test_elo_tiers():
    """Verify tier boundaries."""
    assert get_elo_tier(900) == "Bronze"
    assert get_elo_tier(1100) == "Silver"
    assert get_elo_tier(1200) == "Gold"
    assert get_elo_tier(1500) == "Platinum"
    assert get_elo_tier(1700) == "Diamond"
    assert get_elo_tier(1900) == "Master"
    assert get_elo_tier(2100) == "Grandmaster"

def test_elo_floor():
    """ELO should not go below 100."""
    new_elo, meta = calculate_elo_change(150, 2000, False, 5, True, False)
    assert new_elo >= 100
```

### Integration Tests

**File**: `waffen-tactics-web/backend/tests/test_elo_integration.py` (NEW)

```python
import pytest
from services.combat_service import prepare_combat, process_combat_results
from waffen_tactics.models.player_state import PlayerState

def test_elo_calculation_in_combat():
    """Test that ELO is calculated and saved after combat."""
    # Create test player
    player = PlayerState(
        user_id=12345,
        username="TestPlayer",
        elo_rating=1200,
        elo_games_played=5,
        provisional=True
    )

    # Simulate combat win
    # ... (mock combat result)

    # Verify ELO changed
    assert player.elo_rating != 1200
    assert player.elo_games_played == 6

def test_elo_saved_to_opponent_team():
    """Test that opponent team snapshot includes ELO."""
    # ... test implementation
    pass

def test_elo_saved_to_leaderboard():
    """Test that leaderboard entry includes peak and final ELO."""
    # ... test implementation
    pass
```

### Manual Testing Checklist

- [ ] New player starts at 1200 ELO
- [ ] First 5 games vs bots don't affect ELO
- [ ] Wins increase ELO, losses decrease it
- [ ] Beating higher-rated opponent gives more ELO
- [ ] Provisional badge shows for first 10 ranked games
- [ ] ELO tier badges display correctly
- [ ] Leaderboard sorts by peak ELO
- [ ] Matchmaking finds opponents within ELO range
- [ ] Combat result shows ELO change notification
- [ ] Peak ELO is tracked correctly
- [ ] Database migration runs without errors

---

## Configuration & Tuning

### Adjustable Parameters

**File**: `waffen-tactics-web/backend/services/elo_calculator.py`

```python
# ELO System Configuration
CONFIG = {
    'BASE_ELO': 1200,              # Starting ELO for new players
    'PROVISIONAL_GAMES': 10,       # Games before leaving provisional status
    'K_FACTOR_PROVISIONAL': 40,    # High volatility for new players
    'K_FACTOR_NORMAL': 24,         # Standard K-factor
    'K_FACTOR_HIGH_RATED': 16,     # Lower K for established high-rated players
    'HIGH_RATED_THRESHOLD': 2000,  # ELO threshold for reduced K-factor
    'MATCHMAKING_WINDOWS': [100, 200, 400],  # ELO search windows
    'ELO_FLOOR': 100,              # Minimum possible ELO
}
```

### Recommended Tuning After Launch

**Week 1-2**: Monitor initial rating distribution
- Adjust `BASE_ELO` if too many players cluster at start
- Check if `K_FACTOR_PROVISIONAL` is too volatile

**Week 3-4**: Analyze matchmaking quality
- Adjust `MATCHMAKING_WINDOWS` if matches are too unbalanced
- Consider adding time-based fallback (faster matching after 30s wait)

**Month 1**: Review tier distribution
- Adjust tier thresholds if too many/few players in each tier
- Consider adding more tiers (Elite, Legend, etc.)

**Month 2+**: Fine-tune K-factors
- Reduce volatility if ratings swing too much
- Increase if ratings converge too slowly

---

## Rollout Strategy

### Phase 1: Silent Launch (Week 1)
- Deploy ELO calculation but don't show in UI
- Log all ELO changes for monitoring
- Verify calculations are correct
- Check for edge cases

### Phase 2: Soft Launch (Week 2)
- Show ELO in combat results (small notification)
- Don't change matchmaking yet
- Gather player feedback
- Monitor rating distribution

### Phase 3: Matchmaking Integration (Week 3)
- Enable ELO-based matchmaking
- Keep round-based as fallback
- Monitor match quality metrics
- Adjust windows if needed

### Phase 4: Full Launch (Week 4)
- Update leaderboard to rank by ELO
- Add tier badges and visual flair
- Announce ELO system to players
- Celebrate top-ranked players

---

## Migration Strategy for Existing Players

### Option A: Fresh Start (Recommended)
- All players start at 1200 ELO
- First 10 games are provisional
- Fair but resets existing skill differentials

### Option B: Win-Rate Seeding
- Estimate initial ELO from win rate:
  ```python
  initial_elo = 1200 + (win_rate - 0.5) * 400
  # 60% win rate → 1240 ELO
  # 50% win rate → 1200 ELO
  # 40% win rate → 1160 ELO
  ```
- Less accurate but preserves some skill info

### Option C: Hybrid Approach
- Start at 1200 but use higher K-factor (40) for first 10 games
- Rating converges quickly to true skill
- Best balance of fairness and accuracy

**Recommended**: Use **Option C (Hybrid)** for smoothest transition.

---

## Known Issues & Edge Cases

### System Bot ELO
**Issue**: Bots don't have meaningful ELO ratings

**Solution**:
- Assign bots fixed ELO based on difficulty
- Early bots: 800-1000 ELO
- Don't update player ELO from bot matches

### Inactive Players
**Issue**: Players who quit at high ELO stay on leaderboard forever

**Solution**:
- Mark players inactive after 7 days
- Remove from live leaderboard
- Keep in all-time leaderboard

### ELO Inflation/Deflation
**Issue**: Average ELO can drift over time if win/loss are not balanced

**Solution**:
- Monitor average ELO across all players
- Adjust new player starting ELO if average drifts >50 points
- Periodic "ELO reset seasons" (optional)

### Smurf Accounts
**Issue**: Skilled players can create new accounts to dominate lower ELO

**Solution**:
- High K-factor during provisional games makes smurfs rise quickly
- Monitor for suspicious win streaks
- Consider linking accounts to prevent abuse

---

## Success Metrics

### Week 1 KPIs
- ELO distribution follows normal curve (mean ~1200, std dev ~150)
- No calculation errors in logs
- Average rating change per game: 15-25 points

### Month 1 KPIs
- 80%+ of matches within ±200 ELO
- Player retention improves (fairer matches = more fun)
- Leaderboard shows diverse player pool (not just early adopters)

### Long-term KPIs
- Top 10% players above 1400 ELO
- Bottom 10% below 1000 ELO
- Clear skill progression visible in player ELO history

---

## Documentation & Communication

### Player-Facing Documentation

**FAQ Section**:
- What is ELO rating?
- How is ELO calculated?
- Why did I gain/lose X points?
- What are ELO tiers?
- Do bot matches affect ELO?

**In-Game Tutorial**:
- Show ELO explanation after first ranked match
- Highlight provisional period (first 10 games)
- Explain tier system

### Developer Documentation

**Code Comments**:
- Explain ELO formula and constants
- Document matchmaking windows and fallbacks
- Note edge cases (bots, provisional, etc.)

**Architecture Diagram**:
```
Combat Flow:
1. Fetch opponent (with ELO)
2. Run combat simulation
3. Determine winner
4. Calculate ELO change
5. Update player ELO
6. Save to database
7. Return ELO event to frontend
```

---

## Summary

This plan provides a complete, production-ready ELO rating system for Waffen Tactics with:

✅ **Fair matchmaking** - Players face opponents of similar skill
✅ **Accurate rankings** - Better players naturally rise to top
✅ **Smooth integration** - Minimal changes to existing code
✅ **Robust handling** - Accounts for bots, provisional players, edge cases
✅ **Full UI updates** - Shows ELO in combat results, leaderboard, opponent preview
✅ **Testing coverage** - Unit and integration tests included
✅ **Monitoring** - Logging and metrics for post-launch tuning

The system is designed to work with your existing round-based matchmaking as a fallback, ensuring players always find matches while gradually improving match quality through ELO-based pairing.

**Next Steps**:
1. Run database migration to add ELO fields
2. Implement `elo_calculator.py`
3. Integrate into `game_combat.py` combat flow
4. Update frontend UI components
5. Test with small player group
6. Roll out gradually using phased launch plan

**Estimated Implementation Time**: 2-3 days for backend, 1-2 days for frontend, 1 day for testing = **4-6 days total**
