# Next Steps: Catch the Stun Bug in Action

## Current Status

✅ **Debugging tools created and working**
✅ **Test proves effects DON'T persist in isolation**
❌ **But YOUR desync still shows stuns at seq=1!**

This means the bug happens **only in your specific scenario**. We need to capture it!

## Quick Actions (Do These Now)

### 1. Add Backend Logging (5 minutes)

Edit `waffen-tactics-web/backend/routes/game_combat.py`:

**After line 333**, add:
```python
# DEBUG: Check if effects cleared properly
print("="*80)
print("[DESYNC DEBUG] Effects after clearing:")
for u in player_units:
    if u.effects:
        print(f"  PLAYER {u.id} ({u.name}): {len(u.effects)} effects = {u.effects}")
for u in opponent_units:
    if u.effects:
        print(f"  OPPONENT {u.id} ({u.name}): {len(u.effects)} effects = {u.effects}")
if not any(u.effects for u in player_units + opponent_units):
    print("  ✅ All units have 0 effects")
print("="*80)
```

### 2. Run Backend in Terminal

```bash
cd waffen-tactics-web/backend
python3 api.py
```

Keep this terminal visible so you can see the debug output.

### 3. Trigger the Combat That Shows Desync

- Open your web UI
- Start a combat
- Watch the backend terminal

**Look for:** Any units showing effects after the "Effects after clearing" log

### 4. Capture Frontend Events

When desync appears, open browser console immediately:

```javascript
// Download events
eventLogger.downloadLog('desync_events.json')

// Check first 10 events
eventLogger.getEvents().slice(0, 10).forEach((e, i) => {
  console.log(`${i}: seq=${e.seq} type=${e.type}`)
})

// Check for early stuns
eventLogger.getEventsByType('unit_stunned').forEach(e => {
  console.log(`Stun: seq=${e.seq}, unit=${e.event.unit_id}, duration=${e.event.duration}`)
})
```

## What to Look For

### Scenario A: Backend Shows Effects After Clear
```
[DESYNC DEBUG] Effects after clearing:
  OPPONENT opp_5 (maxas12): 1 effects = [{'type': 'stun', 'duration': 1.5}]
```

**This means:**
- Effects NOT actually cleared
- OR added after clearing
- Bug is in `prepare_opponent_units_for_combat()` or similar

### Scenario B: Backend Shows 0 Effects
```
[DESYNC DEBUG] Effects after clearing:
  ✅ All units have 0 effects
```

**This means:**
- Backend clears correctly
- Effects added DURING combat initialization
- Bug is in `combat_simulator.py` or synergy application

### Scenario C: Backend Logs Nothing

**This means:**
- Combat code path is different than expected
- OR desync happens in different combat
- Need to add logging earlier in the function

## Expected Timeline

1. **Add logging** - 5 minutes
2. **Restart backend** - 1 minute
3. **Trigger combat** - 2 minutes
4. **Capture logs** - 2 minutes
5. **Analyze** - 5 minutes

**Total: ~15 minutes to identify the exact source!**

## After You Capture Logs

Share:
1. **Backend terminal output** (the "DESYNC DEBUG" section)
2. **Frontend events file** (`desync_events.json`)
3. **DesyncInspector output** (the JSON showing the diff)

With these three pieces, we can pinpoint EXACTLY where the phantom stuns come from!

## Alternative: Use Existing Tools

If you can't modify backend right now:

```bash
# Run with your actual game state
cd waffen-tactics-web/backend

# If you have a saved combat that shows desync:
python3 debug_desync.py desync_events.json

# Look for effects in first snapshot:
python3 debug_desync.py desync_events.json 2>&1 | grep -A5 "seq.*1"
```

## Why This Will Work

The test I created proves effects DON'T persist in basic scenarios. But your desync IS real!

This means it's triggered by:
- Specific units (Fiko, maxas12)
- Specific synergies
- Specific game state
- Or web backend code path

The logging will show us **exactly when effects appear** and we'll fix it at the source!

---

**Ready to catch the bug? Add that logging and let's see what happens! 🔍🐛**
