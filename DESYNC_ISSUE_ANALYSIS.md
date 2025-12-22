# Desync Issue Analysis

## Observed Desync in Production

### Affected Units
- **FalconBalkon (opponent)**:
  - HP: UI=786, Server=620 (diff: +166)
  - Attack: UI=83, Server=68 (diff: +15)
  - Effects: UI=[], Server=[{debuff, attack, -15, duration: 4}]

- **Hyodo888 (player)**:
  - Attack: UI=65, Server=85 (diff: -20)
  - Effects: UI=[], Server=[{buff, attack, +20, duration: 3}]

- **Un4given (opponent)**:
  - Attack: UI=52, Server=37 (diff: +15)

- **maxas12 (opponent)**:
  - HP: UI=1280, Server=1220 (diff: +60)

### Pattern Analysis

**Key observation**: Server has effects in `game_state`, frontend has empty `effects: []`

This indicates one of two scenarios:
1. **Effects not being added to frontend state** when stat_buff events arrive
2. **Effects being removed prematurely** (before server removes them)
3. **Snapshot including expired effects** (backend bug)

## Test Results

### Reproduction Attempt
Created combat with exact team composition:
- Opponent: FalconBalkon(2*), Un4given(2*), Dumb(3*), maxas12(3*), Beudzik(2*), Fiko(1*)
- Player: maxas12(1*), Mrozu(1*), V7(2*), Hyodo888(2*), Noname(1*), Pepe(1*)

**Result**: ✅ NO DESYNC in standalone simulator

This indicates the issue is specific to **web backend event emission** or **synergy buff handling**.

## Root Cause Hypothesis

### Likely Cause: Synergy Buffs vs Skill Buffs

The standalone simulator only emits stat_buff events from skills. But the web backend also has:
1. **Synergy buffs** (from faction/class traits)
2. **Persistent buffs** (stored across rounds)

These may be:
- Emitted without proper `buff_type` field
- Not tracked as effects in `game_state`
- Applied differently between backend state and snapshot generation

### Code Evidence

**Frontend code** ([applyEvent.ts:194](vscode-file://vscode-app/usr/share/code/resources/app/out/vs/code/electron-sandbox/workbench/workbench.html)):
```typescript
const effectType = event.buff_type === 'debuff' ? 'debuff' : 'buff'
const effect: EffectSummary = {
  type: effectType,  // Defaults to 'buff' if buff_type is null
  stat: event.stat,
  expiresAt: event.duration ? ctx.simTime + event.duration : undefined,
  applied_delta: delta
}
// Effect is added to unit.effects array
newU.effects = [...(u.effects || []), effect]
```

**Effect expiration** ([applyEvent.ts:549-557](vscode-file://vscode-app/usr/share/code/resources/app/out/vs/code/electron-sandbox/workbench/workbench.html)):
```typescript
// Expire effects based on current simTime
newState.playerUnits = newState.playerUnits.map(u => ({
  ...u,
  effects: u.effects?.filter(e => !e.expiresAt || e.expiresAt > newState.simTime) || []
}))
```

Effects expire automatically EVERY event based on `simTime`. If the backend snapshot includes effects that should have expired, frontend will correctly filter them out, causing a desync.

## Investigation Steps

### 1. Check Web Backend Synergy Application

Look at how synergies are applied in `waffen-tactics-web/backend/services/combat_service.py`:

```python
# Are synergy buffs emitted as stat_buff events?
# Or are they only applied to initial state?
```

### 2. Check Snapshot Effect Inclusion

In `combat_simulator.py`, snapshot generation:

```python
def _build_snapshot_data(self, time, team_a, team_b, ...):
    # Are effects included in unit serialization?
    # Are expired effects filtered out before snapshot?
```

### 3. Check Missing buff_type Field

Search for stat_buff emissions without `buff_type`:

```bash
grep -r "emit.*stat_buff" --include="*.py" | grep -v "buff_type"
```

### 4. Capture Actual Game Events

Save the event stream from the actual failing game combat:

```python
# In game_combat.py, add event logging
with open(f'logs/combat_events_{timestamp}.json', 'w') as f:
    json.dump(all_events, f)
```

Then replay with `test-event-replay.mjs` to see exact desync point.

## Recommended Fixes

### Fix 1: Ensure buff_type is Always Set

In all `emit_stat_buff` calls:

```python
def emit_stat_buff(self, unit, stat, value, duration, is_debuff=False):
    payload = {
        'unit_id': unit.id,
        'stat': stat,
        'value': value,
        'duration': duration,
        'buff_type': 'debuff' if is_debuff else 'buff',  # ✅ Always set
        'buff_type': 'debuff' if value < 0 else 'buff',  # ✅ Or infer from value
        # ...
    }
```

### Fix 2: Track Effects in Backend State

Ensure `CombatUnit` tracks active effects:

```python
class CombatUnit:
    def __init__(self, ...):
        self.active_effects = []  # Track effects with expiry

    def add_effect(self, effect_id, type, stat, value, duration):
        self.active_effects.append({
            'id': effect_id,
            'type': type,
            'stat': stat,
            'value': value,
            'duration': duration,
            'expires_at': self.current_time + duration
        })

    def remove_expired_effects(self, current_time):
        self.active_effects = [
            e for e in self.active_effects
            if e['expires_at'] > current_time
        ]
```

### Fix 3: Include Effects in Snapshots

When building `game_state`:

```python
unit_dict = {
    'id': unit.id,
    'hp': current_hp,
    'attack': unit.attack,
    'effects': unit.active_effects,  # ✅ Include tracked effects
    # ...
}
```

### Fix 4: Frontend - Add Effect ID to Track Removals

In `applyEvent.ts`, when creating effects:

```typescript
const effect: EffectSummary = {
  id: event.effect_id,  // ✅ Use backend effect ID
  type: effectType,
  stat: event.stat,
  // ...
}
```

This allows `effect_expired` events to properly remove effects by ID.

## Next Steps

1. ✅ Add event logging to actual game combat
2. ⬜ Capture event stream from failing scenario
3. ⬜ Replay with test harness to identify exact desync point
4. ⬜ Fix backend to track effects properly
5. ⬜ Ensure all stat_buff events have buff_type field
6. ⬜ Verify snapshots filter expired effects
7. ⬜ Re-test with production event streams

## Files to Check

- `waffen-tactics-web/backend/services/combat_service.py` - Synergy application
- `waffen-tactics-web/backend/routes/game_combat.py` - Event streaming
- `waffen-tactics/src/waffen_tactics/services/combat_simulator.py` - Snapshot generation
- `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py` - Event emission
- `waffen-tactics-web/src/hooks/combat/applyEvent.ts` - Effect tracking
- `waffen-tactics-web/src/hooks/combat/desync.ts` - Desync detection
