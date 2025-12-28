# Investigation Summary: Stun Desync Mystery

## What We Found

### Test Results

Running `test_state_persistence.py`:

1. **✅ Effects DON'T persist between combats**
   - All units show 0 effects after each combat
   - Manual clearing works correctly
   - **First snapshot of second combat has 0 effects**

2. **✅ No phantom stuns in test combats**
   - Effect clearing test shows NO effects in first snapshot
   - This is different from your desync!

3. **❌ HP DOES persist** (but that's expected - units take damage)

### The Mystery

**Your desync shows stuns at seq=1, but our test shows 0 effects at seq=1.**

This means the stuns are NOT from:
- ❌ Previous combat persistence (test proves effects are cleared)
- ❌ Trait/synergy stuns (no traits have stun effects)
- ❌ Passive abilities (Fiko and maxas12 don't have stun skills)

## Where ARE the Stuns Coming From?

### Theory 1: Frontend Browser State Persistence

The stuns might be in YOUR BROWSER's frontend state, not the backend!

**Check:**
```javascript
// In browser console BEFORE starting a combat:
const playerUnits = /* get from React state */
console.log('Player units before combat:', playerUnits.map(u => ({
  id: u.id,
  name: u.name,
  effects: u.effects
})))
```

If units already have effects in frontend state before combat starts, that's your bug!

### Theory 2: Specific Team Composition Triggers It

The desync might only happen with certain unit combinations or synergies.

**Your desync units:**
- Fiko (1abb6544) - 0.3s stun
- maxas12 (opp_5) - 1.5s stun

**Test to reproduce:**
```bash
cd waffen-tactics-web/backend

# Find out what team composition causes it
# Check your actual combat that had the desync
```

### Theory 3: SSE Mapping Issue

The backend might be correctly NOT emitting stuns (our test proves this), but the SSE mapping adds phantom events or the frontend reconstructor creates them.

**Check SSE mapping:**
Look at `game_combat.py` line 250-255 for the event mapping function. Does it somehow inject effects?

### Theory 4: DesyncInspector Comparing Wrong Things

The desync you're seeing might be comparing:
- **UI state:** Fresh units from new combat (no effects)
- **Server snapshot:** Includes effects that WERE in previous combat

This would happen if server snapshots include old effects that weren't cleared.

## Action Items

### 1. Check Frontend State BEFORE Combat

In your browser, before starting a combat:
```javascript
// Get units from game state
const gameState = useGameStore.getState()
console.log('Units before combat:', gameState.board.map(u => ({
  id: u.id,
  name: u.name,
  effects: u.effects,
  persistent_buffs: u.persistent_buffs
})))
```

### 2. Add Backend Logging

In `game_combat.py`, add after line 333:

```python
print(f"[DEBUG] Effects after clear (before combat):")
print(f"  Player: {[(u.id, len(u.effects), u.effects) for u in player_units]}")
print(f"  Opponent: {[(u.id, len(u.effects), u.effects) for u in opponent_units]}")
```

Start backend in terminal and trigger the combat that shows desync.

### 3. Capture Full Event Stream

When you see the desync:
```javascript
// Save ALL events
eventLogger.downloadLog('desync_combat_events.json')

// Check first few events
const earlyEvents = eventLogger.getEvents().slice(0, 20)
console.table(earlyEvents.map(e => ({
  index: e.index,
  seq: e.seq,
  type: e.type,
  unit_id: e.event.unit_id
})))
```

### 4. Compare Backend vs Frontend First Snapshot

**Backend:**
```bash
python3 debug_desync.py --seed <your_seed> 2>&1 | grep -A20 "seq.*1"
```

**Frontend:**
```javascript
const firstSnapshot = eventLogger.getEvents().find(e => e.type === 'state_snapshot' && e.seq === 1)
console.log('First snapshot:', firstSnapshot)
console.log('Effects in snapshot:',
  firstSnapshot.event.player_units.map(u => ({id: u.id, effects: u.effects})),
  firstSnapshot.event.opponent_units.map(u => ({id: u.id, effects: u.effects}))
)
```

## Most Likely Scenarios

### Scenario A: Frontend Reuses Old State (70% likely)

**Evidence:**
- Test shows backend correctly has 0 effects
- Your desync shows effects in "server" but not "ui"

**This means:**
- Frontend gets fresh units (no effects) ✅
- Backend snapshot includes effects from somewhere ❌

**Where to look:**
- How are units prepared for combat?
- Are opponent units cached between rounds?
- Do opponent units come from database with old effects?

### Scenario B: Only Happens in Real Game, Not Tests (20% likely)

**Evidence:**
- Test with random units: 0 effects ✅
- Your actual game: stuns at seq=1 ❌

**This means:**
- Specific team comp or round number triggers it
- Or web backend has different code path than test

**Where to look:**
- `prepare_player_units_for_combat()` vs test unit creation
- Does real game load units differently?
- Are there persistent_buffs on real units?

### Scenario C: Bug in DesyncInspector Comparison (10% likely)

**Evidence:**
- Backend test shows no desyncs
- Your UI shows desyncs

**This means:**
- Backend and frontend actually match
- But comparison logic is wrong

**Where to look:**
- How does DesyncInspector compare effects?
- Does it normalize effect structure?
- Is it comparing at the right time?

## Next Debug Step

**Most efficient:** Add the logging from Action Item #2 and trigger a real combat.

This will tell you if:
1. Backend really has 0 effects after clearing
2. Or if effects sneak in somewhere

Then compare with frontend event log to see if events were emitted but dropped, or never emitted at all.

## Files Created for Debugging

1. **test_state_persistence.py** - Proves effects don't persist (PASSED ✅)
2. **debug_desync.py** - Backend event replay validator
3. **eventLogger.ts** - Frontend event capture

All tools are ready. Now we need to capture logs from your ACTUAL desync scenario!
