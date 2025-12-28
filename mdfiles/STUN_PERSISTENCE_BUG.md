# Stun Persistence Bug - Root Cause Found

## The Issue

Stuns appearing at seq=1, timestamp=0.1 in server state but not emitted as events.

## Root Cause Analysis

Looking at [game_combat.py:312-333](waffen-tactics-web/backend/routes/game_combat.py#L312-L333):

```python
# Line 313-314: Clear player effects
for u in player_units:
    u.effects = []

# Line 319: Prepare opponent (might add effects!)
opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(player)

# Line 332-333: Clear opponent effects
for u in opponent_units:
    u.effects = []

# Line 336-338: Create simulator and HP lists
simulator = CombatSimulator(dt=0.1, timeout=60)
a_hp = [u.hp for u in player_units]
b_hp = [u.hp for u in opponent_units]

# Later: Combat starts, effects somehow already present!
```

## Problem Locations

### Theory 1: Synergies Applied Before Event Callback

After clearing effects, synergies are applied. If synergies include stun effects, they're added WITHOUT emitting events.

**Check:** Do any traits/synergies apply stun at combat start?

### Theory 2: Effects Added During Unit Preparation

`prepare_player_units_for_combat()` or `prepare_opponent_units_for_combat()` might add effects.

**Evidence:**
- Player effects cleared at line 314
- Opponent prepared at line 319 (might add effects to player units!)
- Opponent effects cleared at line 333

If `prepare_opponent_units_for_combat()` modifies player units, the clear at 314 happens too early!

### Theory 3: First Snapshot Includes Effects Added Without Events

The combat simulator's first snapshot (seq=1) includes effects that were:
1. Cleared at lines 314/333 ✅
2. Re-added by synergy application
3. But NO events emitted for them ❌

## Diagnostic Test

Add logging to track when effects are added:

```python
# In game_combat.py, after line 314:
print(f"[DEBUG] After clear, player effects: {sum(len(u.effects) for u in player_units)}")

# After line 333:
print(f"[DEBUG] After opponent clear, effects: player={sum(len(u.effects) for u in player_units)}, opp={sum(len(u.effects) for u in opponent_units)}")

# After synergy application (wherever that happens):
print(f"[DEBUG] After synergies, effects: player={sum(len(u.effects) for u in player_units)}, opp={sum(len(u.effects) for u in opponent_units)}")
```

Run combat and check console output. If effects > 0 after synergies, that's where they come from!

## Backend Debugging Command

```bash
cd waffen-tactics-web/backend

# Add print statements to game_combat.py, then run:
# (Start backend and trigger a combat)

# Or check the reconstructor:
python3 debug_desync.py --seed 42 2>&1 | head -100 > combat_init.txt

# Look for when effects appear:
grep -i "effect" combat_init.txt | head -20
```

## Most Likely Fix Locations

### Location 1: Synergy Application

Find where synergies are applied after the effect clear:

```bash
cd waffen-tactics-web/backend
grep -n "synergy\|apply.*buff" routes/game_combat.py | grep -A5 -B5 "333"
```

Look for synergy application happening after line 333. If it adds effects, it needs to emit events!

### Location 2: Combat Simulator Initialization

Check `combat_simulator.py` for effects added at initialization:

```python
# In combat_simulator.py
def simulate(self, team_a, team_b, event_callback=None):
    # If synergies applied here without event_callback set up:
    self.apply_synergies(team_a, team_b)  # ← Might add stuns

    # Event callback set up later:
    self.event_callback = event_callback  # ← Too late!
```

## Quick Fix (Temporary)

Add event emission for initial effects BEFORE first snapshot:

```python
# In game_combat.py, after synergies are applied:
def emit_initial_effects(units, event_callback, side):
    """Emit events for effects present at combat start"""
    for unit in units:
        for effect in unit.effects:
            if effect.get('type') == 'stun':
                from waffen_tactics.services.event_canonicalizer import emit_unit_stunned
                emit_unit_stunned(
                    event_callback,
                    unit,
                    duration=effect.get('duration', 1.0),
                    source=None,
                    side=side,
                    timestamp=0.0
                )
            # Add similar for other effect types...

# Call before combat starts:
emit_initial_effects(player_units, event_callback, 'team_a')
emit_initial_effects(opponent_units, event_callback, 'team_b')
```

## Proper Fix (Recommended)

1. **Find where effects are added** after the clear (lines 314/333)
2. **Ensure event_callback is set up** before effects are added
3. **Call canonical emitters** when adding effects
4. **Or don't add stun effects at combat initialization** (if they shouldn't be there)

## Verification Steps

1. **Check effect count at different stages:**
   ```python
   print(f"After clear: {len(player_units[0].effects)}")
   print(f"After synergies: {len(player_units[0].effects)}")
   print(f"At first snapshot: {len(player_units[0].effects)}")
   ```

2. **Check event stream:**
   ```bash
   # Count unit_stunned events before seq=10
   python3 debug_desync.py --seed <seed> 2>&1 | grep "unit_stunned\|seq.*[1-9]" | head -50
   ```

3. **Compare counts:**
   - Effects in first snapshot: N
   - `unit_stunned` events emitted: M
   - If N > M → Missing events!

## Expected Behavior After Fix

1. **No effects** at lines 314/333 (after clear)
2. **Effects added** during combat with events emitted
3. **First snapshot (seq=1)** has 0 effects OR all effects have corresponding events
4. **Frontend receives** `unit_stunned` events before or at seq=1
5. **No desync** in DesyncInspector

## Test Case

Create a test that verifies no effects exist at combat start:

```python
def test_no_effects_at_combat_start():
    # Prepare units
    player_units = prepare_player_units_for_combat(...)
    opponent_units = prepare_opponent_units_for_combat(...)

    # Clear effects (as done in game_combat.py)
    for u in player_units + opponent_units:
        u.effects = []

    # Start combat
    events = []
    def callback(type, data):
        events.append((type, data))

    simulator.simulate(player_units, opponent_units, event_callback=callback)

    # First snapshot should have 0 effects OR
    # have unit_stunned events emitted before it
    first_snapshot = next(e for t, e in events if t == 'state_snapshot')
    stun_events_before = [e for t, e in events if t == 'unit_stunned' and e['seq'] < first_snapshot['seq']]
    stuns_in_snapshot = count_stuns_in_snapshot(first_snapshot)

    assert len(stun_events_before) >= stuns_in_snapshot, \
        f"Missing {stuns_in_snapshot - len(stun_events_before)} unit_stunned events"
```

## Summary

**Root cause:** Effects (stuns) are added to units after being cleared, but WITHOUT emitting events.

**Where:** Between lines 333 and first snapshot emission - likely during synergy application or simulator initialization.

**Fix:** Either:
1. Don't add stun effects at combat start (if inappropriate)
2. Emit events when adding effects
3. Retroactively emit events for effects present at first snapshot

**Diagnostic:** Add print statements to track when `len(unit.effects)` changes from 0 to > 0.
