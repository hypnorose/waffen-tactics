# Combat Event Reconstruction - Architectural Analysis

**Date**: 2025-12-20
**Status**: CRITICAL - Event Sourcing Principles Violated
**Impact**: ~400 lines of game logic in reconstructor that should be in backend

---

## Executive Summary

The `CombatEventReconstructor` has become a **"shadow game engine"** that replicates complex game logic instead of being a simple event replay system. This violates core event sourcing principles and causes:

- **Desyncs** on edge cases where reconstructor logic differs from backend
- **Unmaintainable code** - game logic duplicated in two places
- **Broken UI replay** - animations don't match actual game state
- **Hard to debug** - unclear which events are missing vs. which logic is wrong

**Recommendation**: Treat this as **technical debt that MUST be paid**. Every line of game logic in the reconstructor is a place where UI can desync from backend.

---

## CRITICAL VIOLATIONS OF EVENT SOURCING PRINCIPLES

### 🔴 VIOLATION #1: Snapshot Reconciliation (Lines 540-756)
**Location**: `combat_event_reconstructor.py:540-756` (`reconcile_effects`)

**Problem**: Reconstructor **patches missing events by copying data from snapshots**.

```python
# Lines 540-756: reconcile_effects()
for eff in snap_u.get('effects', []):
    # ... complex logic to detect missing effects ...
    if has_equivalent(recon_u.get('effects', []), eff):
        continue
    # ❌ VIOLATION: Applying effects that were never emitted as events!
    recon_u['shield'] = recon_u.get('shield', 0) + amt
    recon_u['effects'].append(new_eff)
```

**Why This Breaks Determinism**:
- Reconstructor **invents effect application logic** that should have been explicit events
- If effect exists in snapshot but not in reconstructed state, **backend forgot to emit the event**
- UI cannot replay correctly because event stream is incomplete

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. Add missing event emissions for all effect applications
2. Every `unit.effects.append(...)` in backend MUST have corresponding event
3. Add validation: `assert len(events_emitted) == len(effects_applied)`

---

### 🔴 VIOLATION #2: Synthetic 'expires_at' Derivation (Lines 817-829)
**Location**: `combat_event_reconstructor.py:817-829` (`_expire_effects`)

```python
# Lines 817-829
if 'expires_at' not in e or e.get('expires_at') is None:
    if e.get('type') == 'damage_over_time' and e.get('ticks_remaining') is not None:
        interval = float(e.get('interval', 0) or 0)
        ticks = int(e.get('ticks_remaining') or 0)
        next_tick = float(e.get('next_tick_time', current_time) or current_time)
        # ❌ VIOLATION: Computing expires_at from ticks_remaining/interval
        e['expires_at'] = next_tick + max(0, (ticks - 1)) * interval
```

**Why This Breaks Determinism**:
- Reconstructor **derives complex game logic** (tick scheduling math)
- Computation may not match backend's actual expiration logic
- If backend changes tick calculation, reconstructor desyncs

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. `damage_over_time_applied` event MUST include authoritative `expires_at`
2. Never emit DoT effects with `None` expires_at unless they truly never expire
3. Backend computes `expires_at` once at application time, not per-tick

---

### 🔴 VIOLATION #3: Percentage Buff Delta Calculation (Lines 363-379)
**Location**: `combat_event_reconstructor.py:363-379` (`_process_stat_buff_event`)

```python
# Lines 363-379
delta = event_data.get('applied_delta')
if delta is None:
    if value_type == 'percentage':
        pct = float(amount if amount is not None else (value or 0))
        base_stats = unit_dict.get('base_stats') or {}
        if isinstance(base_stats, dict) and stat in base_stats:
            base = base_stats.get(stat, 0) or 0
        else:
            base = unit_dict.get(stat, 0) or 0
        # ❌ VIOLATION: Computing percentage buff delta locally
        delta = int(round(base * (pct / 100.0)))
```

**Why This Breaks Determinism**:
- Reconstructor uses **local base_stats** which may diverge from backend state
- Rounding behavior may differ between Python versions/platforms
- If backend changes percentage formula (e.g., floor vs round), reconstructor breaks

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. `stat_buff` events MUST always include `applied_delta` (already in event_canonicalizer.py:118)
2. Never emit percentage buffs without computing numeric delta on backend
3. Validate: `assert 'applied_delta' in payload` before emitting

**STATUS**: ✅ Partially fixed - `emit_stat_buff` includes `applied_delta` at line 118, but need to ensure all callers use canonical emitter

---

### 🔴 VIOLATION #4: 'random' Stat Inference (Lines 631-667)
**Location**: `combat_event_reconstructor.py:631-667` (reconcile_effects → random stat handling)

```python
# Lines 631-667
if stat == 'random':
    candidates = ['attack', 'defense', 'attack_speed', 'hp', 'max_hp', 'current_mana', 'max_mana']
    chosen = None
    # ... loop trying every candidate stat ...
    for cand in candidates:
        recon_val = recon_u.get(cand, 0) or 0
        snap_val = snap_u.get(cand, None)
        # ❌ VIOLATION: Guessing which stat was actually buffed!
        if recon_val + expected == snap_val:
            chosen = cand
            break
```

**Why This Breaks Determinism**:
- Reconstructor **guesses game logic** by trial-and-error
- If two stats coincidentally satisfy equation, picks wrong one
- **NOT deterministic** - depends on snapshot ordering

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. **NEVER emit `stat: 'random'` in events**
2. Backend resolves random stat selection BEFORE event emission
3. Event always includes concrete stat that was modified (e.g., `stat: 'attack'`)

---

### 🔴 VIOLATION #5: Damage Event HP Fallback (Lines 134-136)
**Location**: `combat_event_reconstructor.py:134-136` (`_process_damage_event`)

```python
# Lines 132-136
if new_hp is not None:
    unit_dict['hp'] = new_hp
elif damage > 0:
    # ❌ VIOLATION: Fallback calculation instead of authoritative HP
    unit_dict['hp'] = max(0, old_hp - damage)
```

**Why This Breaks Determinism**:
- If `target_hp` missing from event, reconstructor **computes HP locally**
- May not match backend (e.g., overkill protection, min HP limits)
- Leads to HP desyncs on edge cases

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. ALL damage events MUST include authoritative `target_hp` or `new_hp`
2. Never emit attack events without post-damage HP
3. Already done in `emit_damage` - ensure all callers use it

---

### 🔴 VIOLATION #6: DoT Tick HP Fallback (Lines 263-270)
**Location**: `combat_event_reconstructor.py:263-270` (`_process_dot_event`)

```python
# Lines 263-270
if 'unit_hp' in event_data:
    unit_dict['hp'] = event_data.get('unit_hp')
elif 'target_hp' in event_data:
    unit_dict['hp'] = event_data.get('target_hp')
elif 'new_hp' in event_data:
    unit_dict['hp'] = event_data.get('new_hp')
else:
    # ❌ VIOLATION: Computing HP delta locally
    unit_dict['hp'] = max(0, unit_dict['hp'] - damage)
```

**Why This Breaks Determinism**:
- Same issue as damage events - local computation may not match backend
- DoT ticks may have special logic (immunity, resistance) not replicated here

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. ALL `damage_over_time_tick` events MUST include authoritative `unit_hp`
2. Backend is source of truth for post-tick HP
3. Never emit tick events without final HP value

---

### 🔴 VIOLATION #7: Skill Cast Mana Reset Hardcoded (Line 328)
**Location**: `combat_event_reconstructor.py:328` (`_process_skill_cast_event`)

```python
# Line 328
if unit_id:
    unit_dict = self._get_unit_dict(unit_id)
    if unit_dict:
        unit_dict['current_mana'] = 0  # ❌ VIOLATION: Hardcoded game logic!
```

**Why This Breaks Determinism**:
- Assumes all skill casts set mana to 0
- What if future skills have variable mana costs?
- What if some skills refund mana?
- This is **GAME LOGIC in reconstructor**

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. Emit explicit `mana_update` event after skill cast
2. `skill_cast` event should NOT imply mana changes
3. All mana changes must be explicit `mana_update` events

---

### 🔴 VIOLATION #8: Shield Absorption Calculation (Line 139)
**Location**: `combat_event_reconstructor.py:139` (`_process_damage_event`)

```python
# Line 139
unit_dict['shield'] = max(0, unit_dict.get('shield', 0) - shield_absorbed)
```

**Why This Breaks Determinism**:
- Shield absorption is **game logic** (priority, order, overflow handling)
- What if backend has shield caps, DR modifiers, etc.?

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. Damage events MUST include authoritative `remaining_shield` or `new_shield`
2. Don't force reconstructor to compute `shield -= absorbed`
3. Backend knows final shield value, emit it directly

---

### 🔴 VIOLATION #9: Effect Expiration Stat Reversion (Lines 836-855)
**Location**: `combat_event_reconstructor.py:836-855` (`_expire_effects`)

```python
# Lines 836-855
for unit_dict, effect in expired_effects:
    if etype in ('buff', 'debuff'):
        stat = effect.get('stat')
        delta = effect.get('applied_delta', 0) or 0
        # ❌ VIOLATION: Revert stat by subtracting delta
        if stat:
            unit_dict[stat] = unit_dict.get(stat, 0) - delta
```

**Why This Breaks Determinism**:
- Assumes buff expiration means "subtract the delta"
- What if backend has decay mechanics, diminishing returns, buff interactions?
- This is **complex game logic** hidden in reconstructor

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. Emit explicit `effect_expired` events with authoritative post-expiration stats
2. Event should include: `{ effect_id, unit_id, new_attack, new_defense, ... }`
3. Never force reconstructor to guess stat reversion

---

### 🔴 VIOLATION #10: Snapshot Authoritative Overwrite (Lines 738-740)
**Location**: `combat_event_reconstructor.py:738-740` (`reconcile_effects`)

```python
# Lines 738-740
for field in ('hp', 'max_hp', 'current_mana', 'max_mana', 'attack', 'defense', 'attack_speed', 'shield'):
    if field in snap_u:
        recon_u[field] = snap_u[field]  # ❌ VIOLATION: Overwriting reconstructed state!
```

**Why This Breaks Determinism**:
- This **ADMITS DEFEAT** - reconstructor cannot replay events correctly
- Instead of fixing event emissions, papering over bugs by copying snapshot data
- UI cannot smoothly interpolate state because events don't match snapshots

**This should be fixed in the backend, not the reconstructor.**

**Backend Fix Required**:
1. **Remove this line entirely** - it's a band-aid over missing events
2. If reconstruction diverges from snapshot, **THE EVENTS ARE WRONG**
3. Add assertions that fail loudly instead of silently patching

---

## ⚠️ MODERATE ISSUES

### Issue #1: DoT Tick Deduplication (Lines 227-238)

The reconstructor has complex logic to deduplicate DoT ticks. **Why is backend emitting duplicate events?**

**Backend Fix**: Ensure each DoT tick is emitted exactly once with tick ID or sequence tracking.

---

### Issue #2: Multiple HP Field Names (Lines 117-122, 263-268)

Reconstructor checks for `target_hp`, `new_hp`, and `unit_hp`. **Pick ONE canonical field name.**

**Backend Fix**: Standardize on `unit_hp` for all post-mutation HP values. Remove aliases.

---

### Issue #3: Stun Effects Ignored (Lines 861-862)

```python
if effect.get('type') == 'stun':
    return None  # ignore stun for now
```

If stuns affect combat, they must be reconstructible.

**Backend Fix**: Ensure `unit_stunned` events are complete. Add `stun_expired` events.

---

## 📋 REQUIRED BACKEND CHANGES

### Priority 1: Critical (Block Release)

1. ✅ **Always emit `applied_delta` in stat_buff events**
   - Already implemented in event_canonicalizer.py:118
   - Validate all callers use canonical emitter

2. **Never emit `stat: 'random'` in events**
   - Backend must resolve random stat BEFORE emission
   - Event includes concrete stat name

3. **All damage/DoT events must include authoritative HP**
   - Add `unit_hp` to all attack, damage_over_time_tick events
   - Remove fallback calculations from reconstructor

4. **Emit explicit mana_update after skill casts**
   - Don't assume mana=0, emit actual post-cast mana

5. **All DoT effects must have authoritative `expires_at`**
   - Compute on backend, not derived from ticks_remaining

---

### Priority 2: Important (Ship Next Sprint)

6. **Add `new_shield` to damage events**
7. **Emit `effect_expired` with authoritative stats**
8. **Remove snapshot reconciliation entirely** (Lines 540-756)
   - If snapshot differs from reconstruction, **FAIL THE TEST**
9. **Standardize HP field names** (use `unit_hp` consistently)
10. **Fix DoT tick deduplication at source**

---

### Priority 3: Polish (Technical Debt)

11. **Add stun expiration events**
12. **Add event schema validation**
13. **Generate TypeScript types from event schemas**

---

## 🎯 ARCHITECTURAL PRINCIPLE VIOLATIONS

The reconstructor currently violates:

1. ❌ **"Reconstructor should be dumb"** - Contains game logic (HP calc, stat reversion, random stat inference)
2. ❌ **"All state from events"** - Copies from snapshots instead
3. ❌ **"Events are truth"** - Overwrites event-derived state with snapshots
4. ❌ **"No guessing"** - Guesses random stats, expires_at, shield values
5. ❌ **"Backend is authoritative"** - Computes deltas, HP, expirations locally

---

## ✅ CORRECT PATTERNS IN RECONSTRUCTOR

These parts are good and should be kept:

1. **Lines 110-141** - Process damage with authoritative HP (when `target_hp` present)
2. **Lines 155-182** - Mana updates with authoritative values
3. **Lines 183-192** - Heal events with amount only
4. **Lines 415-435** - Stun event processing (simple effect append)

---

## 🔧 IMMEDIATE ACTION ITEMS

### For Backend Team:

1. Audit all `emit_stat_buff` callers - ensure `applied_delta` always provided
2. Find all places that emit `stat: 'random'` - resolve concrete stat before emission
3. Add `unit_hp` to all damage/DoT events
4. Add schema validation to event emitters
5. Remove snapshot reconciliation logic - let tests fail to reveal missing events

### For Reconstructor:

1. Remove lines 540-756 (reconcile_effects) entirely
2. Remove lines 817-829 (expires_at derivation)
3. Remove lines 363-379 (percentage delta calculation) - require applied_delta
4. Remove lines 631-667 (random stat inference) - error if stat=='random'
5. Remove lines 738-740 (snapshot overwrite) - fail instead
6. Make all fallback calculations error loudly instead of computing

---

## 📊 IMPACT ASSESSMENT

**Lines of hidden game logic in reconstructor**: ~400 lines
**Lines that should be in backend**: ~350 lines
**Lines that should error instead of patch**: ~50 lines

**Estimated Effort**:
- Backend fixes: 2-3 days (add missing events, schema validation)
- Reconstructor simplification: 1 day (remove logic, add assertions)
- Testing and validation: 1-2 days

**Risk if NOT Fixed**:
- Desyncs will continue on edge cases
- UI replays will show incorrect animations
- Spectator mode will diverge from actual game
- Hard to debug which events are missing

---

## 🎯 CONCLUSION

The reconstructor has become a "shadow game engine" which defeats the purpose of event sourcing. **Every line of game logic in the reconstructor is a place where UI can desync from backend.**

**FINAL RECOMMENDATION**: Treat this as technical debt that MUST be paid. Prefer adding more explicit events over smarter reconstruction.

---

**Last Updated**: 2025-12-20
**Author**: Claude Sonnet 4.5
**Priority**: CRITICAL
**Blocking**: UI replay accuracy, spectator mode, event sourcing integrity
