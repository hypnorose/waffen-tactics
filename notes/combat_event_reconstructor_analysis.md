# Combat Event Reconstructor Analysis

## Overview
Analysis of the `CombatEventReconstructor` class in `/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend/services/combat_event_reconstructor.py` for issues in event-sourced state reconstruction. The goal is to ensure reconstructed state matches authoritative snapshots deterministically.

## Key Issues Identified

### 1. Missing State Mutations on Effect Expiration (Major Determinism Breaker)
- **Lines**: 218-225 (`_expire_effects`), 152-185 (`_process_stat_buff_event`), 118-135 (`_process_shield_applied_event`)
- **Problem**: Effects expire and are removed, but stat changes (buffs/debuffs) and shield values are not reverted. Reconstructed state keeps permanent modifications.
- **Impact**: Diverges from snapshots where effects are expired and stats reverted.
- **Fix**: Store reversion deltas in effects and apply them on expiration.

### 2. Incorrect Assumptions About Event Fields and State Derivation
- **Lines**: 50-65 (`_process_damage_event`), 152-185 (`_process_stat_buff_event`), various
- **Problem**: Assumes fields like `shield_absorbed`, caps HP at `max_hp` (immutable), `'dead'` is stored but should be derived.
- **Impact**: Breaks if fields are missing or `max_hp` is mutable; `'dead'` can desync.
- **Fix**: Derive `'dead'` purely from `hp == 0`, validate fields, handle `max_hp` buffs if needed.

### 3. Order-of-Events Bugs and Missing Event Types
- **Lines**: 25-45 (`process_event`)
- **Problem**: Events like `'skill_cast'` are unhandled but mutate state (e.g., mana reset). No explicit expiration events.
- **Impact**: Missed mutations lead to divergence.
- **Fix**: Add handlers for missing events.

### 4. State Mutated but Never Reconstructed vs. Reconstructed but Never Emitted
- **Lines**: 152-185, 195 (`_process_state_snapshot_event`)
- **Problem**: `'buffed_stats'` in snapshots but not reconstructed/checked. Effects reconstructed but may not be fully evented.
- **Impact**: Incomplete reconstruction.
- **Fix**: Either reconstruct `'buffed_stats'` or remove from snapshots; ensure all mutations are evented.

### 5. Event Naming/Schema Inconsistencies
- **Lines**: 25-45, event handlers
- **Problem**: Similar events have different names/schemas (e.g., `'heal'` vs. `'unit_heal'`), missing fields.
- **Impact**: Assumptions cause wrong calculations.
- **Fix**: Standardize schemas in reconstructor; require fields.

## Proposed Fixes
- Implement reversion logic for effects.
- Derive `'dead'` and update comparisons.
- Add missing event handlers.
- Store deltas in effects for reversion.
- Validate event fields.

## Invariants Violated
- State must be fully reversible via events.
- Reconstruction must match snapshots.
- Events processed in `seq` order must be deterministic.