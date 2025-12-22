# Deployment Checklist - Desync Fixes

## Pre-Deployment Verification ✅

All fixes have been:
- ✅ Implemented in code
- ✅ Tested with comprehensive test suites
- ✅ Validated with real scenarios (Miki's stun skill)
- ✅ Documented thoroughly

---

## Files Changed (Summary)

### Backend
- `waffen-tactics/src/waffen_tactics/services/effects/stun.py`
  - Now uses `emit_unit_stunned` canonical emitter
  - Fixes stun events missing

### Frontend
- `waffen-tactics-web/src/hooks/combat/applyEvent.ts`
  - Line 134: Fixed HP damage calculation (removed double shield subtraction)
  - Lines 214-224: Removed buffed_stats mutation in stat_buff handler
  - Lines 563-571: Removed buffed_stats mutation in effect expiration

---

## Deployment Steps

### Step 1: Stop Services
```bash
./stop-all.sh
```

### Step 2: Rebuild Frontend
```bash
cd waffen-tactics-web
npm run build
```

**Expected output**: Build completes successfully without errors

### Step 3: Restart Services
```bash
cd ..
./start-all.sh
```

### Step 4: Verify Services Running
```bash
./status.sh
```

**Expected**: All services (backend, frontend, discord bot if applicable) running

---

## Post-Deployment Testing

### Test 1: Quick Combat Test
1. Open game in browser
2. Start a combat
3. Watch for DesyncInspector warnings

**Expected**:
- ✅ No HP desync warnings
- ✅ No defense stat desync warnings
- ✅ No effect desync warnings

### Test 2: Check Browser Console
1. Open browser DevTools (F12)
2. Run a combat
3. Look for event logs

**Expected**:
```javascript
// Should see unit_stunned events when stuns occur
[MANA] Event for player_0: current_mana=120, amount=120
⚠️ player_0 casting skill!
// If stun skill: should see unit_stunned event here
```

### Test 3: Monitor Backend Logs
```bash
tail -f waffen-tactics-web/backend/api.log
```

**Expected**:
- No error messages
- `[EMIT_STAT_BUFF]` logs when buffs/debuffs applied
- No AttributeError or TypeError exceptions

---

## Verification Checklist

After deployment, check these conditions:

### HP Consistency ✅
- [ ] UI HP matches server HP in snapshots
- [ ] No cumulative HP drift over long combats
- [ ] Shield absorption working correctly

### Defense Stats ✅
- [ ] `buffed_stats.defense` stays constant
- [ ] `defense` changes when debuffs applied
- [ ] DesyncInspector shows matching defense values

### Stun Events ✅
- [ ] Stun effects have corresponding `unit_stunned` events
- [ ] Effects have proper `effect_id` fields
- [ ] No "phantom" stuns appearing without events

---

## Rollback Plan (If Needed)

If issues occur, rollback by reverting the commits:

### Backend Rollback
```bash
cd waffen-tactics/src/waffen_tactics/services/effects
git checkout HEAD~1 stun.py
```

### Frontend Rollback
```bash
cd waffen-tactics-web/src/hooks/combat
git checkout HEAD~1 applyEvent.ts
```

Then rebuild and restart:
```bash
cd waffen-tactics-web
npm run build
cd ..
./stop-all.sh
./start-all.sh
```

---

## Success Criteria

Deployment is successful if:

1. ✅ All services start without errors
2. ✅ Frontend builds successfully
3. ✅ Combats run without crashes
4. ✅ DesyncInspector shows minimal/no warnings
5. ✅ No new errors in backend logs

---

## Monitoring

For the first few combats after deployment, monitor:

1. **Browser Console**: Look for desync warnings or errors
2. **Backend Logs**: Watch for exceptions or errors
3. **DesyncInspector**: Check for HP, defense, or effect mismatches

If you see **NEW types of desyncs** (not HP, defense, or stun-related), those are separate issues not covered by these fixes.

---

## Contact/Next Steps

After deployment:

1. Run 3-5 test combats
2. Check all verification items above
3. If all checks pass → **You're done!** 🎉
4. If issues persist → Check if they're the SAME desyncs (unlikely) or NEW ones

---

## Quick Reference

### Test Commands
```bash
# Run backend tests
cd waffen-tactics-web/backend
../../waffen-tactics/bot_venv/bin/python test_all_desync_fixes.py
../../waffen-tactics/bot_venv/bin/python test_specific_desync_scenarios.py
```

### Build Commands
```bash
# Frontend build
cd waffen-tactics-web
npm run build

# Backend (no build needed, Python runs directly)
cd waffen-tactics-web/backend
python api.py
```

### Service Commands
```bash
./start-all.sh    # Start all services
./stop-all.sh     # Stop all services
./status.sh       # Check service status
```

---

## Expected Timeline

- **Stop services**: ~30 seconds
- **Frontend build**: ~1-2 minutes
- **Start services**: ~30 seconds
- **Quick test**: ~2 minutes
- **Total**: ~5 minutes

---

## You're Ready! 🚀

All code changes are complete and tested. Just deploy and verify!
