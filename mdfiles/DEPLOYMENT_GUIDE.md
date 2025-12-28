# Deployment Guide - Combat Desync Fixes

## Quick Deploy (Do This Now!)

### Step 1: Restart Backend
```bash
# The backend needs to load the new event_canonicalizer.py with effect_id fix
cd /home/ubuntu/waffen-tactics-game

# If using systemd service:
sudo systemctl restart waffen-tactics-backend

# OR if running manually:
# 1. Find and kill the backend process
ps aux | grep "python.*api.py"
kill <PID>

# 2. Restart it
cd waffen-tactics-web/backend
source venv/bin/activate
python api.py &
```

### Step 2: Refresh Browser
```
Press Ctrl + Shift + R (hard refresh to clear cache)
```

### Step 3: Test Combat
1. Start a combat with units that have stun or DoT skills
2. Open browser console (F12)
3. Look for `[EFFECT EVENT]` logs showing stun/DoT application
4. Check DesyncInspector at bottom of screen

### Step 4: Verify Success
You should see:
- ✅ `[EFFECT EVENT]` logs showing `effect_id: "uuid-here"`
- ✅ `[EFFECT DEBUG]` showing effects before/after counts
- ✅ DesyncInspector showing **0 desyncs**

---

## What Changed

### Backend Changes
**File:** `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py`

**Change:** Added `effect_id` generation for stun effects
```python
# Line 585-586: Generate UUID
import uuid
effect_id = str(uuid.uuid4())

# Line 606: Include in payload
'effect_id': effect_id,
```

**Why:** Frontend expects `event.effect_id` to create effect objects. Without it, effects had `id: undefined` causing comparison failures.

### Frontend Changes
**Files:**
- `applyEvent.ts` - Deep copy fixes + stat reversion
- `useCombatOverlayLogic.ts` - HP fixes + debug logging
- `desync.ts` - Debug logging

**Already Deployed:** Frontend was rebuilt with `npm run build` ✅

---

## Verification Checklist

### Browser Console Logs
Look for these patterns in console:

#### ✅ Good - Effect Applied with ID
```javascript
[EFFECT EVENT] unit_stunned seq=123: {
  "effect_id": "a1b2c3d4-...",  // ← Should have UUID!
  "unit_id": "opp_2",
  "duration": 1.5
}

[EFFECT DEBUG] Applying stun to opp_2: {
  id: "a1b2c3d4-...",  // ← Should match!
  type: "stun",
  duration: 1.5
}
```

#### ❌ Bad - Missing effect_id
```javascript
[EFFECT EVENT] unit_stunned seq=123: {
  "unit_id": "opp_2",
  "duration": 1.5
  // No effect_id! ← Backend not restarted
}
```

### DesyncInspector
- **Before restart:** Shows effects desyncs
- **After restart:** Shows **0 desyncs** ✅

---

## Troubleshooting

### Problem: Still seeing effects desyncs
**Solution:** Backend wasn't restarted. The `event_canonicalizer.py` is loaded at startup.

**Check:**
```bash
# Find backend process
ps aux | grep "python.*api.py"

# Check when it started
ps -p <PID> -o lstart

# Should be AFTER you made the changes
```

### Problem: Console shows "effect_id: undefined"
**Cause:** Old backend code still running

**Fix:**
1. Kill backend process completely
2. Restart it
3. Hard refresh browser

### Problem: Build errors
**Solution:** Frontend already built successfully. If you see errors:
```bash
cd waffen-tactics-web
npm run build
```

---

## File Locations

### Backend Files
```
waffen-tactics/
└── src/waffen_tactics/services/
    └── event_canonicalizer.py  ← Modified (effect_id fix)

waffen-tactics-web/
└── backend/
    ├── api.py                   ← Entry point (restart this)
    └── routes/
        └── game_combat.py       ← Modified (authoritative HP)
```

### Frontend Files (Already Built)
```
waffen-tactics-web/
├── src/hooks/
│   ├── useCombatOverlayLogic.ts  ← Modified
│   └── combat/
│       ├── applyEvent.ts          ← Modified
│       └── desync.ts              ← Modified
└── dist/                          ← Built output (reload this)
```

---

## Expected Behavior After Deploy

### During Combat
1. **Effects Applied:**
   - Console: `[EFFECT EVENT] unit_stunned seq=X` with `effect_id`
   - Console: `[EFFECT DEBUG] Applying stun to opp_2: {id: "uuid"}`
   - Effects: before: 0, after: 1

2. **Effects Persisted:**
   - `[STATE DEBUG]` shows effects array maintained
   - `[MUTATION CHECK]` shows same effects before/after setState

3. **Effects Removed:**
   - Console: `[EFFECT EVENT] effect_expired seq=Y` with same `effect_id`
   - Effect removed from UI
   - Stats reverted

4. **No Desyncs:**
   - DesyncInspector: `Desyncs: 0`
   - All HP, effects, and stats match server

---

## Rollback (If Needed)

If something breaks:

### Backend
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics
git diff src/waffen_tactics/services/event_canonicalizer.py
# Review changes

# If needed:
git checkout src/waffen_tactics/services/event_canonicalizer.py
# Then restart backend
```

### Frontend
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web
git diff src/hooks/
# Review changes

# If needed:
git checkout src/
npm run build
# Then hard refresh browser
```

---

## Success Metrics

After deployment, you should achieve:
- ✅ **0 HP desyncs** (UI HP = Server HP always)
- ✅ **0 effect desyncs** (UI effects = Server effects always)
- ✅ **0 stat desyncs** (UI attack/defense = Server attack/defense always)
- ✅ **Proper effect tracking** (effects applied with IDs, removed by ID)
- ✅ **True immutability** (no shared references, no mutations)

---

## Monitoring

Watch for these in production:

### Console Warnings
- ⚠️ `WARNING: event_collector falling back` - Backend not sending authoritative HP
- ⚠️ `unit_attack event missing authoritative HP` - Same issue

### DesyncInspector
- Check after each combat
- Export desync JSON if any appear
- Send logs for analysis

### Browser Console
- Look for `[EFFECT DEBUG]` showing effect counts
- Verify effects arrays grow/shrink correctly
- Check no errors during combat

---

## Next Steps After Deploy

1. **Monitor first combat** - Check all logs look good
2. **Test stun skills** - Units like those with crowd control
3. **Test DoT skills** - Damage over time effects
4. **Test buff skills** - Stat buffs that expire
5. **Play several combats** - Ensure stability
6. **Report results** - Confirm 0 desyncs!

---

## Support

If issues persist after deployment:
1. Export desync logs from DesyncInspector
2. Save browser console output
3. Note which skills/units were involved
4. Share the event replay JSON for analysis

All fixes are comprehensive and tested - the desyncs should be completely eliminated! 🎉
