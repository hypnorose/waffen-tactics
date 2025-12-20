# Combat Event System Architecture

## Overview
The game uses an event-driven combat system where all combat actions emit events that are:
1. Sent to clients via SSE (Server-Sent Events)
2. Used to reconstruct game state on the frontend
3. Validated in tests to ensure deterministic replay

## Key Components

### 1. Combat Simulator (`waffen-tactics/src/waffen_tactics/services/combat_simulator.py`)
- Runs the combat simulation loop
- Emits events for all combat actions
- Must emit events for: attacks, skills, buffs, heals, shields, mana updates, deaths

### 2. Skill Executor (`waffen-tactics/src/waffen_tactics/services/skill_executor.py`)
- Executes skill effects
- Should emit events for each effect type:
  - `unit_heal` for heal effects
  - `stat_buff` for buff effects
  - `shield_applied` for shield effects
  - `mana_update` for mana deductions

### 3. Event Reconstructor (`waffen-tactics-web/backend/services/combat_event_reconstructor.py`)
- Rebuilds game state from event stream
- Used on frontend to replay combat
- CRITICAL: Must stay in sync with actual combat state

## Current Issues (2025-12-19)

### Issue 1: Missing `mana_update` Events
**Test:** `test_mana_accumulation_and_skill_casting`
**Problem:** Skill casting doesn't emit mana_update events
**Impact:** Frontend can't track mana properly during combat

### Issue 2: Missing `unit_heal` Events
**Tests:** `test_skill_support_effects_in_combat_emit_heal_buff_shield`, `test_heal_buff_shield_mapped_have_names`
**Problem:** Heal effects in skills don't emit unit_heal events
**Impact:** Healing is invisible to clients; UI can't show heal animations

### Issue 3: HP Reconstruction Desync
**Test:** `test_10v10_simulation_multiple_seeds`
**Problem:** Event replay produces different HP than actual simulation (e.g., 0 vs 410)
**Impact:** Frontend game state diverges from server; breaks trust in combat results
**Seed 2 example:** Mrvlook has 0 HP in simulation but 410 HP in reconstruction

## Event Flow Architecture

```
Combat Simulator
    ↓ (emits events)
Event Stream
    ↓ (splits to)
├─→ Event Reconstructor (rebuilds state from events)
└─→ SSE to Client (frontend displays events)
```

**CRITICAL RULE:** Event stream must be complete and sufficient to rebuild exact game state.
If reconstruction != simulation, the event stream is incomplete/incorrect.

## Design Principles

1. **Event Completeness:** Every state change must have a corresponding event
2. **Event Ordering:** Events must be ordered by sequence number (seq) and timestamp
3. **Determinism:** Same initial state + same events = same final state
4. **Idempotency:** Processing same event twice should be safe (use seq numbers)

## Common Pitfalls

1. ❌ Applying effect but not emitting event (e.g., healing without unit_heal event)
2. ❌ Emitting wrong event type (e.g., 'heal' instead of 'unit_heal')
3. ❌ Missing state in events (e.g., not including new HP after heal)
4. ❌ Processing events out of order in reconstructor
5. ❌ Modifying state without updating event stream

## Testing Strategy

- **Unit Tests:** Test individual components (skill executor, effect handlers)
- **Integration Tests:** Test full combat with event verification
- **Replay Tests:** Verify event stream can reconstruct exact final state
- **Seed Tests:** Run with multiple random seeds to catch non-determinism
