# Phase 5: Event-Based Trait Effects Implementation

## Overview
Implement the missing event-based trait effects that trigger during combat and other game events. Currently, only stat_buff effects work - we need to add support for on_death triggers, mana regeneration, round-based buffs, and other dynamic effects.

## Current Status
- ✅ stat_buff effects: Working (18 effects)
- ✅ per_second_buff effects: Working (3 effects)
- ✅ enemy_debuff effects: Working (3 effects)
- ✅ dynamic_hp_per_loss: Working (1 effect)
- ✅ win_scaling: Working (1 effect)
- ❌ All other effect types: Not implemented

## Missing Effect Types

### Combat Event Effects
- **on_ally_death** (3 effects): Trigger when ally dies
  - Denciak: Gold rewards when allies die
- **on_enemy_death** (11 effects): Trigger when enemy dies
  - Various traits: Healing, gold, mana rewards
- **on_ally_hp_below** (1 effect): Trigger when ally HP drops below threshold

### Passive Effects
- **mana_regen** (3 effects): Passive mana regeneration per second
- **per_round_buff** (4 effects): Buffs that scale with round number

### Shop/Gameplay Effects
- **reroll_free_chance** (1 effect): Chance for free shop rerolls
- **target_least_hp** (1 effect): Smart targeting preference

## Implementation Plan

### Phase 5.1: Combat Event System
1. Create event system in combat simulator
2. Add event hooks for unit death, damage, healing
3. Create event dispatcher for trait effects

### Phase 5.2: Death-Based Effects
1. Implement on_ally_death handlers
2. Implement on_enemy_death handlers
3. Add reward system (gold, mana, healing)

### Phase 5.3: Passive Effects
1. Implement mana_regen in combat
2. Implement per_round_buff scaling
3. Add emergency effects (on_ally_hp_below)

### Phase 5.4: Shop Effects
1. Implement reroll_free_chance
2. Implement target_least_hp AI

## Technical Architecture

### Event System
```python
class CombatEventSystem:
    def __init__(self, synergy_engine, player_state):
        self.synergy_engine = synergy_engine
        self.player_state = player_state
        self.event_handlers = {
            'unit_death': self._handle_unit_death,
            'damage_dealt': self._handle_damage_dealt,
            'combat_start': self._handle_combat_start,
            # etc.
        }

    def trigger_event(self, event_type: str, event_data: dict):
        handler = self.event_handlers.get(event_type)
        if handler:
            handler(event_data)
```

### Effect Handlers
```python
class TraitEffectHandler:
    @staticmethod
    def handle_on_ally_death(trait_effect: dict, event_data: dict, player_state):
        # Process ally death effects
        pass

    @staticmethod
    def handle_on_enemy_death(trait_effect: dict, event_data: dict, player_state):
        # Process enemy death effects
        pass
```

## Integration Points

### With Combat Simulator
- Hook into existing combat loop
- Add event triggers at appropriate points
- Pass player state for rewards/effects

### With Game Manager
- Apply passive effects before combat
- Update player state with rewards
- Handle shop effects in shop service

## Success Metrics
- All 20+ trait effects implemented and working
- Combat feels more dynamic with kill rewards
- Mana regeneration works properly
- Round scaling effects provide progression
- No performance impact on combat speed</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/notes/phase5_trait_effects_design.md