# Quick Deploy Guide - 2 Steps

## 🚀 Deploy Now (2 Commands)

### Step 1: Restart Backend
```bash
pkill -f "python.*api.py" && cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend && source venv/bin/activate && nohup python api.py > backend.log 2>&1 &
```

### Step 2: Refresh Browser
```
Press: Ctrl + Shift + R
```

---

## ✅ Verify Success

Open browser console and look for:
```javascript
[EFFECT EVENT] unit_stunned seq=X: {
  "effect_id": "a1b2c3d4-...",  // ✅ Should have UUID
  ...
}
```

Check DesyncInspector:
```
Desyncs: 0  ✅
```

---

## 🎯 What Was Fixed

1. **HP Desyncs** - UI now uses authoritative backend HP
2. **Effects Desyncs** - Deep copy prevents shared references
3. **Stat Desyncs** - Stats revert when effects expire
4. **Missing IDs** - Backend now sends effect_id for tracking
5. **Auto-Expiration** - Removed client-side timer

---

## 📊 Expected Outcome

**Before:**
- ❌ UI HP ≠ Server HP
- ❌ Effects missing from UI
- ❌ Stats not reverting

**After:**
- ✅ Perfect HP sync
- ✅ Perfect effects sync
- ✅ Perfect stat sync
- ✅ 0 desyncs

---

## 🔧 If Issues Persist

1. Verify backend restarted: `ps aux | grep api.py`
2. Check browser cache cleared: Hard refresh again
3. Review logs: `tail -f backend.log`
4. Test with effect-heavy skills (stuns, DoTs)

---

See `FINAL_STATUS.md` for complete details.
