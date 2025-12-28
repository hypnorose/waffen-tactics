# Next Steps - Event System Improvements

## Current Status ✅

**Test Results**: 301/302 passing (99.7%)
- Fixed 10 previously failing tests
- All skill-related tests pass
- Only 1 remaining failure (expected - OLD skill system bug)

**Recent Improvements**:
1. ✅ All skill effect handlers use canonical emitters
2. ✅ Events contain authoritative HP values (`target_hp`, `unit_hp`, `post_hp`)
3. ✅ **NEW**: Frontend UI properly prioritizes authoritative HP over deltas
4. ✅ **NEW**: `emit_stat_buff()` now ALWAYS includes `applied_delta` for ALL stats
5. ✅ **NEW**: Frontend UI uses `applied_delta` when available (stat_buff handler)
6. ✅ Reconstructor fully documented with architectural violation warnings

## Immediate Task: Fix Last Failing Test

**Test**: `test_10v10_simulation_multiple_seeds` - 2 seeds failing
**Root Cause**: OLD skill system does NOT support `ally_team` heals

### The Bug (`combat_simulator.py:800-813`)

```python
# Line 486 - Called with defending_hp
self._process_skill_cast(unit, defending_team[target_idx], defending_hp, ...)

# Line 808 - Updates defending_hp even for ally heals (WRONG TEAM)
target_hp_list[apply_idx] = min(...)

# Line 812 - emit_unit_heal correctly sets unit.hp (CORRECT)
emit_unit_heal(callback, target_obj, caster, amount, ...)
```

**Result**: `unit.hp` = 286 (correct), `attacking_hp[idx]` = 246 (stale), snapshot desync

### Fix (Choose One)

#### Option 1: Migrate Units to skills.json (RECOMMENDED) ⭐

1. Find units with `ally_team` heals:
   ```bash
   grep -r "ally_team" waffen-tactics/units.json
   ```

2. For each unit (example: Grzałcia):
   - Create skill in `skills.json`:
   ```json
   {
     "id": "healing_aura",
     "name": "Healing Aura",
     "description": "Heal all allies and buff their defense",
     "mana_cost": 50,
     "effects": [
       {
         "type": "HEAL",
         "target": "ALL_ALLIES",
         "params": {"amount": 40}
       },
       {
         "type": "BUFF",
         "target": "ALL_ALLIES",
         "params": {"stat": "defense", "value": 15, "duration": 4}
       }
     ]
   }
   ```

   - Update `units.json`:
   ```json
   {
     "id": "grzalcia",
     "name": "Grzałcia",
     "skills": ["healing_aura"]  // Reference instead of inline
   }
   ```

3. Test:
   ```bash
   cd waffen-tactics-web/backend
   source venv/bin/activate
   python -m pytest tests/test_combat_service.py::TestCombatService::test_10v10_simulation_multiple_seeds -v
   ```

#### Option 2: Add `ally_team` Support to Old System (NOT RECOMMENDED)

Would require:
1. Add target resolution for `ally_team` in `combat_simulator.py:733-758`
2. Make `_process_skill_cast` accept both `attacking_hp` and `defending_hp`
3. Select correct HP list based on whether target is ally or enemy
4. **Adds complexity to legacy code being phased out**

---

## Backend Event Fixes (Post-Test Fix)

### High Priority

- [x] ~~`emit_stat_buff()` includes `applied_delta` for ALL stats~~ ✅ **DONE**
- [ ] Resolve `stat='random'` to concrete stat before emission
- [ ] Emit `stat_buff` events for ALL synergy buff applications
- [ ] Emit `effect_expired` when buffs/debuffs/shields expire
- [ ] Emit `damage_over_time_expired` consistently
- [ ] Prevent DoT tick duplicates via `event_id`

### Implementation Details

#### Random Stat Resolution

**Current**:
```python
# Skills emit stat='random'
emit_stat_buff(callback, unit, stat='random', value=10, ...)
```

**Should Be**:
```python
# Resolve BEFORE emission
if stat == 'random':
    stat = random.choice(['attack', 'defense', 'attack_speed', 'hp'])
emit_stat_buff(callback, unit, stat=stat, value=10, ...)  # Emit resolved stat
```

**Files to modify**:
- Any skill that uses `stat: 'random'`
- Search for: `grep -r "stat.*random" waffen-tactics/`

#### Effect Expiration Events

**Location**: `combat_effect_processor.py`

**Add**:
```python
# In effect expiration loop
for effect in unit.effects:
    if effect.expires_at <= current_time:
        # EMIT EVENT BEFORE REMOVING
        if effect.type == 'damage_over_time':
            emit_damage_over_time_expired(callback, unit, effect_id=effect.id, ...)
        else:
            emit_effect_expired(callback, unit, effect_id=effect.id, ...)
        # Then remove
        unit.effects.remove(effect)
```

#### Synergy Buff Events

**Location**: `synergy.py` - wherever synergy buffs are applied

**Ensure**:
```python
# MUST emit event for every synergy buff
for buff in calculate_synergies(unit):
    # Apply buff
    unit.attack += buff.attack_bonus
    # EMIT EVENT
    emit_stat_buff(callback, unit, stat='attack', value=buff.attack_bonus, ...)
```

---

## Reconstructor Simplifications (After Backend Fixes)

### Can Delete After `applied_delta` Verified

**`combat_event_reconstructor.py:386-416`** - Stat buff delta calculation:
```python
# DELETE THIS (backend now provides applied_delta)
if delta is None:
    if value_type == 'percentage':
        pct = float(amount)
        base_stats = unit_dict.get('base_stats') or {}
        delta = int(round(base * (pct / 100.0)))
    else:
        delta = int(round(amount))

# REPLACE WITH:
delta = event_data.get('applied_delta', 0)  # Trust backend
```

**Lines Saved**: ~30 lines

### Can Delete After Random Stat Resolution

**`combat_event_reconstructor.py:683-716`** (in reconciliation) - Random stat inference:
```python
# DELETE THIS (backend now resolves random to concrete stat)
if stat == 'random':
    candidates = ['attack', 'defense', 'attack_speed', 'hp']
    for cand in candidates:
        # ... complex inference logic ...
```

**Lines Saved**: ~35 lines

### Can Delete After Effect Expiration Events

**`combat_event_reconstructor.py:859-906`** - Entire `_expire_effects()` function:
```python
# DELETE ENTIRE FUNCTION
def _expire_effects(self, current_time: float):
    # 50 lines of synthetic expiration logic
```

**Lines Saved**: ~50 lines

### Can Simplify After All Effect Events

**`combat_event_reconstructor.py:606-848`** - Replace reconciliation with strict validation:
```python
# REPLACE 240 lines of reconciliation with:
def reconcile_effects(snapshot_units, reconstructed_units):
    # Just validate - DO NOT apply effects from snapshots
    for uid, snap_u in snapshot_units.items():
        recon_u = reconstructed_units[uid]
        if snap_u['effects'] != recon_u['effects']:
            raise AssertionError(f"Effect mismatch - backend forgot to emit event!")
```

**Lines Saved**: ~230 lines

### Total Simplification

**Current**: 1050 lines
**After Cleanup**: ~300 lines ✅
**Deleted**: ~750 lines of workarounds

---

## Documentation

### Completed ✅

- `CANONICAL_EMITTER_FIXES.md` - Session summary for canonical emitter migration
- `RECONSTRUCTOR_ARCHITECTURAL_ANALYSIS.md` - Full reconstructor violation analysis
- `BACKEND_FIXES_APPLIED.md` - Summary of backend fixes applied
- `combat_event_reconstructor.py` - All violations marked with ❌ and TODO comments

### Key Documents

1. **NEXT_STEPS.md** (this file) - High-level roadmap
2. **RECONSTRUCTOR_ARCHITECTURAL_ANALYSIS.md** - Deep dive on violations
3. **BACKEND_FIXES_APPLIED.md** - What's been fixed vs what remains
4. **CLAUDE.md** - Architecture reference

---

## Success Criteria

### Immediate (Unblock Tests)
- [ ] Migrate units with `ally_team` heals to skills.json
- [ ] All 302 tests pass (100%)

### Short Term (Event Quality)
- [x] ~~`emit_stat_buff` includes applied_delta~~ ✅ **DONE**
- [ ] Random stat buffs emit resolved stat
- [ ] All effect applications emit events
- [ ] All effect expirations emit events
- [ ] DoT ticks are unique (no duplicates)

### Long Term (Architectural)
- [ ] Reconstructor reduced to <300 lines
- [ ] No fallback calculations in reconstructor
- [ ] No reconciliation from snapshots
- [ ] No synthetic state derivation
- [ ] Snapshots used ONLY for validation (fail on mismatch)

---

## Verification Commands

### Run All Tests
```bash
source waffen-tactics/bot_venv/bin/activate
python -m pytest waffen-tactics/tests/ waffen-tactics-web/backend/tests/ -v
```

### Run Just the Failing Test
```bash
cd waffen-tactics-web/backend
source venv/bin/activate
python -m pytest tests/test_combat_service.py::TestCombatService::test_10v10_simulation_multiple_seeds -v
```

### Run Skill Tests
```bash
# Core skill tests
cd waffen-tactics
python -m pytest tests/test_skill_effect_events.py \
                 tests/test_comprehensive_system.py::TestSkillParserAndEffects \
                 tests/test_delayed_skills_events.py -v

# Web backend skill tests
cd waffen-tactics-web/backend
python -m pytest tests/test_skill_effects.py \
                 tests/test_skills_in_combat.py \
                 tests/test_sse_mapping.py -v
```

---

## Key Principles Going Forward

### 1. Always Use Canonical Emitters
- ✅ **DO**: Use `emit_damage()`, `emit_unit_heal()`, `emit_stat_buff()`, etc.
- ❌ **DON'T**: Manually mutate `unit.hp`, `unit.shield`, or create events directly

### 2. Events Must Be Sufficient For Reconstruction
- ✅ **DO**: Include authoritative post-state values (`unit_hp`, `applied_delta`)
- ❌ **DON'T**: Emit only deltas and expect reconstructor to calculate final state

### 3. Snapshots Are Validation Checkpoints
- ✅ **DO**: Compare reconstructed state to snapshots and FAIL on mismatch
- ❌ **DON'T**: Apply missing effects from snapshots (masks backend bugs)

### 4. Reconstructor Should Be Dumb
- ✅ **DO**: Apply events in sequence, trust event data
- ❌ **DON'T**: Add formulas, inference, or recovery logic

### 5. If Reconstruction Requires Guessing
- **THE EVENT SCHEMA IS WRONG** - fix the backend, not the reconstructor

---

## Progress Tracking

- [x] All skill handlers use canonical emitters
- [x] Events contain authoritative HP
- [x] Backend reconstructor prioritizes authoritative HP
- [x] **Frontend UI prioritizes authoritative HP** ✅ **NEW**
- [x] `emit_stat_buff` includes `applied_delta` for all stats
- [x] **Frontend UI uses `applied_delta`** ✅ **NEW**
- [x] Reconstructor violations fully documented
- [ ] **Fix ally_team heal bug** ← **NEXT TASK**
- [ ] All 302 tests pass
- [ ] Random stat resolution
- [ ] Effect expiration events
- [ ] Synergy buff events
- [ ] Delete reconstructor fallback logic
- [ ] Delete reconciliation logic
- [ ] Delete synthetic expiration
- [ ] Delete frontend fallback logic
- [ ] Reconstructor <300 lines
