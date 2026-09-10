# Deployment Checklist - Desync Fixes

> **Status / release boundary:** This is a historical checklist for the
> desync-fix work. It is not a release approval and its checkmarks do not
> prove Game View, deployment, VPS, or rollback acceptance. Use
> [`docs/RELEASE_VALIDATION_GATE.md`](../docs/RELEASE_VALIDATION_GATE.md) as
> the canonical current gate on the exact revision intended for deployment.

## Pre-Deployment Automated Evidence

The historical desync fixes were implemented and covered by automated tests.
That evidence must remain separate from authenticated Game View, post-deploy
VPS checks, screenshots, and release-owner approval.

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

Run these steps only as an explicitly authorized deployment. Before starting,
follow the revision-alignment and pre-deployment sections in the canonical
release gate.

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

If issues occur, stop the rollout and preserve the local revision, VPS
`HEAD`, status, and logs. Do **not** use `git checkout HEAD~1` on individual
files: that is not a reproducible release rollback and can create an
unreviewed mixed tree.

Choose a release-owner-approved known-good commit, verify it with the
canonical release gate, and deploy that exact revision through the documented
deployment procedure. Record the rollback revision, failure owner, and
post-rollback status/log evidence in Plane.

---

## Automated Evidence Only

This historical checklist can establish only that:

1. ✅ All services start without errors
2. ✅ Frontend builds successfully
3. ✅ Combats run without crashes
4. ✅ Automated desync/replay checks pass for the covered scenarios

It cannot establish authenticated Game View acceptance, public deployment
health, visual readability at target resolutions, or rollback readiness.

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
3. If automated checks pass, continue with the canonical release gate and
   record the required manual/runtime evidence in Plane.
4. If issues persist, classify them as the same regression or a new issue and
   preserve the evidence before changing the runtime.

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

## Release Gate Handoff

This file alone never authorizes release. Use the canonical release gate and
leave the final go/no-go decision, runtime evidence, and any waiver in Plane.
