# TODO: Implement Mana Gain on Damage Taken

## Current Status
As of 2025-12-20, units only gain mana from:
- ✅ Attacking (via `mana_on_attack` stat)
- ✅ Passive regeneration (via `mana_regen` stat)
- ✅ Per-second buff effects
- ✅ Skill effects

## Missing Feature
❌ **Mana gain when taking damage** - Units do NOT gain mana when hit by enemies

## Implementation Plan

### 1. Add `mana_on_take_damage` stat to unit models
- Update `waffen-tactics/src/waffen_tactics/models/unit.py` (Stats class)
- Add field: `mana_on_take_damage: int = 0  # mana gained when taking damage`

### 2. Update unit role definitions
- Edit `waffen-tactics/unit_roles.json` to define per-role values
- Example values:
  - Tank: 15 (gains more mana when hit)
  - Damage: 5
  - Support: 8
  - Assassin: 3

### 3. Update combat processors
Location: `waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py`

After damage is dealt (around line 50-70), add:
```python
# Defender gains mana from taking damage
defender = defending_team[target_idx]
if hasattr(defender, 'stats') and hasattr(defender.stats, 'mana_on_take_damage'):
    mana_gain = defender.stats.mana_on_take_damage
    if mana_gain > 0 and defending_hp[target_idx] > 0:  # Only if still alive
        defender.mana = min(defender.max_mana, defender.mana + mana_gain)

        # Emit mana update event
        if event_callback:
            from .event_canonicalizer import emit_mana_change
            defending_side = 'team_b' if side == 'team_a' else 'team_a'
            emit_mana_change(event_callback, defender, mana_gain, side=defending_side, timestamp=time)
```

### 4. Update data loader
Location: `waffen-tactics/src/waffen_tactics/services/data_loader.py`

Update Stats initialization to include `mana_on_take_damage` (around line 55):
```python
Stats(
    # ... existing fields ...
    mana_on_attack=role_stats.get('mana_on_attack', 10),
    mana_on_take_damage=role_stats.get('mana_on_take_damage', 5),  # NEW
    mana_regen=role_stats.get('mana_regen', 5)
)
```

### 5. Frontend updates
✅ No changes needed - frontend already handles `mana_update` events correctly via `applyEvent.ts:231-257`

### 6. Testing
Create test in `waffen-tactics/tests/test_mana_on_damage.py`:
```python
def test_defender_gains_mana_when_hit():
    """Verify that units gain mana when taking damage"""
    # Setup attacker and defender with mana_on_take_damage stat
    # Simulate attack
    # Assert defender mana increased by expected amount
    # Verify mana_update event was emitted
```

### 7. Balance considerations
- Tank units should gain MORE mana per hit (they take more hits)
- Damage dealers should gain LESS mana per hit (they take fewer hits)
- Consider capping mana gain from damage (e.g., max once per second per unit)
- Alternatively, scale mana gain by damage taken (% of max HP)

## References
- Similar mechanic in TFT: Units gain mana from auto-attacks AND taking damage
- Current mana system: `waffen-tactics/src/waffen_tactics/models/unit.py:11`
- Attack processor: `waffen-tactics/src/waffen_tactics/services/combat_attack_processor.py:46-70`
- Event canonicalizer: `waffen-tactics/src/waffen_tactics/services/event_canonicalizer.py:201-223`
