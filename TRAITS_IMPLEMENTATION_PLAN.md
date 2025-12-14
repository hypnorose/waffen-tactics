# Traits Implementation Plan

## Current Status
After reviewing `traits.json`, the following effect types are defined:

### Implemented Effects ✅
- `stat_buff`: Static stat bonuses (HP, attack, defense, attack_speed)
- `per_trait_buff`: Bonus per active synergy
- `dynamic_hp_per_loss`: HP bonus based on losses
- `win_scaling`: Scaling bonuses per wins
- `on_enemy_death`: Buffs when killing enemies
- `on_ally_death`: Effects when allies die
- `hp_regen_on_kill`: HP regen after kills
- `mana_regen`: Increased mana regen
- `target_least_hp`: Targeting behavior
- `on_ally_hp_below`: Healing allies below HP threshold
- `buff_amplifier`: Amplifies other buffs
- `per_round_buff`: Bonuses that increase per round
- `reroll_free_chance`: Free shop reroll chance (handled in GameManager)

### Not Implemented Effects ❌ → ✅ **IMPLEMENTED**
- `enemy_debuff`: ✅ Debuffs applied to enemy team stats (used by "Prostaczka")
- `stat_steal`: ✅ Steals stats from enemies (used by "Haker") 
- `on_sell_bonus`: ✅ Extra gold/XP on unit sales (used by "Konfident")

## Implementation Plan ✅ **COMPLETED**

### 1. Enemy Debuff (`enemy_debuff`) ✅
**Status**: Implemented
- Added `apply_enemy_debuffs()` in `SynergyEngine`
- Applied in `CombatManager.start_combat()` to opponent units
- Tested with "Prostaczka" trait

### 2. Stat Steal (`stat_steal`) ✅
**Status**: Implemented
- Added stat steal logic in `combat_shared.py` during kill events
- Steals percentage of killed enemy's defense and adds to killer
- Works for "Haker" trait

### 3. On Sell Bonus (`on_sell_bonus`) ✅
**Status**: Implemented
- Enhanced `UnitManager.sell_unit()` to accept `active_synergies`
- Applies gold per star level and XP bonuses when selling
- Works for "Konfident" trait

### 4. General Enhancements
- **Effect Validation**: Add tests for each new effect type.
- **Documentation**: Update comments in `traits.json` for clarity.
- **Balance Tuning**: Test synergies in combat to ensure balance.
- **Edge Cases**: Handle multiple effects stacking, negative values, etc.

## Priority Order
1. `enemy_debuff` (affects combat balance)
2. `stat_steal` (complex, needs combat integration)
3. `on_sell_bonus` (simple, enhances economy)

## Testing Strategy
- Unit tests for each effect in `test_synergy_engine.py`.
- Integration tests with combat simulations.
- Manual testing with specific trait combinations.

## Risks
- Complex effects may introduce bugs in combat simulation.
- Performance impact from additional calculations per tick.
- Balance issues if effects are too strong/weak.</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/TRAITS_IMPLEMENTATION_PLAN.md