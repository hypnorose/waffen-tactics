# Stun at Combat Start - Debugging Guide

## The Issue

Stuns appearing at **seq=1-4, timestamp=0.1** (first combat tick), detected during `mana_update` events.

## Key Observation

The desync note says: `"event mana_update diff (opponent)"`

This means:
1. **Stun was applied BEFORE seq=1** (during combat initialization)
2. **No `unit_stunned` event was emitted**
3. **First snapshot (seq=1) includes the stun**
4. **Frontend never received the event, so no stun in UI**

## Likely Root Causes

### 1. Synergy/Trait Applying Stun at Combat Start

Some trait or synergy might apply stun to units before combat loop starts.

**Check:**
```bash
cd waffen-tactics
# Search for combat start hooks
grep -rn "combat.*start\|initialize.*combat" src/ | grep -i stun

# Search for trait effects that apply at start
grep -rn "on_combat_start\|battle_start\|combat_init" traits.json
```

### 2. Passive Ability Applied During Unit Setup

Skills with passive effects might be applied before event emission is set up.

**Check:**
```bash
# Search for passive stun effects
grep -rn "passive.*stun\|aura.*stun" src/

# Look at combat simulator initialization
grep -A 30 "def simulate" waffen-tactics/src/waffen_tactics/services/combat_simulator.py | grep -i stun
```

### 3. Events Emitted Before event_callback Is Set Up

The combat simulator might emit events for initial state before the callback is properly wired.

**Check combat_simulator.py:**
```python
def simulate(self, team_a, team_b, event_callback=None):
    # If synergy buffs are applied HERE, before setting up event system:
    apply_synergies(team_a, team_b)  # ← Might apply stuns without emitting

    # Then event system initialized:
    self.event_callback = event_callback

    # Combat loop starts - too late to emit the initial stuns!
```

## Diagnostic Steps

### Step 1: Check What Units Have Stuns

From your desync:
- **maxas12** (opp_5) - 1.5s stun
- **Fiko** (1abb6544) - 0.3s stun

**Action:**
```bash
cd waffen-tactics
# Find these units
grep -i "maxas12\|fiko" units.json -A 20 | grep -i "skill\|passive\|stun"
```

Look for:
- Skills that apply stun on combat start
- Passive abilities
- Special traits

### Step 2: Check Event Stream for unit_stunned

**Backend:**
```bash
cd waffen-tactics-web/backend
# Simulate and check for unit_stunned events at start
python3 debug_desync.py --seed <seed> 2>&1 | head -100 | grep -i "unit_stunned\|seq.*1\|seq.*2"
```

**Expected:** Should see `unit_stunned` events BEFORE seq=1
**If not:** Events are not being emitted at all

**Frontend:**
```javascript
// In browser console after combat
const earlyEvents = eventLogger.getEvents().filter(e => e.seq <= 5)
console.table(earlyEvents.map(e => ({
  seq: e.seq,
  type: e.type,
  unit_id: e.event.unit_id,
  timestamp: e.timestamp
})))

// Look for unit_stunned
const stunEvents = earlyEvents.filter(e => e.type === 'unit_stunned')
console.log('Early stun events:', stunEvents)
```

**Expected:** `unit_stunned` events for maxas12 and Fiko
**If not:** Events never reached frontend

### Step 3: Check Synergy Application Timing

**Location:** `waffen-tactics/src/waffen_tactics/services/synergy.py` or combat_service.py

Look for where synergies are applied:
```python
# PROBLEM: Synergies applied before event_callback set up
def prepare_combat(team_a, team_b, event_callback=None):
    # Apply synergies (might include stuns)
    synergy_engine.apply_buffs(team_a, team_b)  # ← No event emission!

    # Later, create simulator with callback
    simulator = CombatSimulator(event_callback=event_callback)
    # Too late - stuns already applied!
```

**Fix:**
```python
# CORRECT: Pass event_callback to synergy application
def prepare_combat(team_a, team_b, event_callback=None):
    simulator = CombatSimulator(event_callback=event_callback)

    # Apply synergies with event emission
    synergy_engine.apply_buffs(team_a, team_b, event_callback=event_callback)

    # Now events will be emitted!
```

## Most Likely Scenario

Based on the pattern (multiple units, seq=1, 0.1s timestamp):

**Initial combat state snapshot includes stuns that were applied during setup WITHOUT emitting events.**

The sequence is:
1. Combat initialization
2. Units created with base stats
3. **Synergies/passives applied → Stuns added to unit.effects**
4. **Event callback set up** ← Too late!
5. First tick (t=0.1s)
6. **First snapshot emitted (seq=1)** ← Includes stuns
7. Frontend never got `unit_stunned` events ← Desync!

## Fix Approaches

### Approach 1: Emit Events for Initial State (Recommended)

After applying all initial effects, explicitly emit events for them:

```python
def simulate(self, team_a, team_b, event_callback=None):
    # Apply synergies
    apply_synergies(team_a, team_b)

    # Emit events for initial effects
    if event_callback:
        for unit in team_a + team_b:
            for effect in unit.effects:
                if effect.get('type') == 'stun':
                    emit_unit_stunned(
                        event_callback,
                        unit,
                        duration=effect.get('duration'),
                        source=effect.get('source'),
                        side=get_side(unit),
                        timestamp=0.0  # Initial time
                    )
```

### Approach 2: Apply Synergies After Event System Setup

Move synergy application to happen after event callback is configured:

```python
def simulate(self, team_a, team_b, event_callback=None):
    self.event_callback = event_callback

    # NOW apply synergies - events will be emitted
    self.apply_synergies(team_a, team_b)

    # Start combat loop
    ...
```

### Approach 3: Don't Apply Stuns During Initialization

If stuns shouldn't happen at combat start, remove them from initial setup:

```python
# In synergy application or unit setup
# Don't apply stun effects during initialization
# Only apply stat buffs
for effect in synergy_effects:
    if effect['type'] != 'stun':  # Skip stuns at init
        apply_effect(unit, effect)
```

## Quick Test

Run the diagnostic script:

```bash
cd waffen-tactics-web/backend

# Run with verbose output, capture first 200 lines
python3 debug_desync.py --seed <seed> 2>&1 | head -200 > combat_start.txt

# Check for early events
grep "seq.*[0-9]" combat_start.txt | head -20

# Look for unit_stunned before first snapshot
grep -B5 "state_snapshot.*seq.*1" combat_start.txt | grep unit_stunned
```

**If no `unit_stunned` events appear before first snapshot:**
→ Stuns are applied without event emission
→ Need Approach 1 or 2 above

## Expected Fix Location

Most likely in one of these files:
- `waffen-tactics/src/waffen_tactics/services/combat_simulator.py` - Combat initialization
- `waffen-tactics/src/waffen_tactics/services/synergy.py` - Synergy application
- `waffen-tactics-web/backend/services/combat_service.py` - Combat preparation

Look for where effects are applied to units before the combat loop starts.

## Verification After Fix

1. **Backend test:**
```bash
python3 debug_desync.py --seed <seed> 2>&1 | head -50
# Should show unit_stunned events at timestamp=0.0 or very early
```

2. **Frontend test:**
```javascript
const earlyStuns = eventLogger.getEvents()
  .filter(e => e.type === 'unit_stunned' && e.timestamp < 0.2)
console.log('Early stun events:', earlyStuns)
// Should show events for maxas12 and Fiko
```

3. **No desync:**
   - DesyncInspector shows no effect mismatches
   - All stuns have corresponding events

## Summary

The stuns at combat start are likely from:
1. **Synergy/trait effects applied during combat setup**
2. **Applied before event emission system is ready**
3. **Resulting in "phantom" stuns - in server state but no events**

Fix by either:
- Emitting events retroactively after initialization
- Moving initialization to happen after event system setup
- Not applying stun effects during initialization (if inappropriate)

The debugging tools will show you exactly when the stuns appear in the state vs when events are emitted!
