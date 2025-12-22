# Modular Trait Effects System - Design Plan

## Current Problems
The current trait effects system has inconsistent structures:
- Some effects use `actions` arrays, others don't
- Properties like `chance`, `trigger_once`, `duration` are scattered
- Hard to add new reward types or conditions
- Trigger logic mixed with reward logic

## Proposed Solution: Unified Modular Structure

### Core Concepts
1. **Triggers**: When the effect activates (on_enemy_death, per_second, etc.)
2. **Conditions**: When/how often it can trigger (chance, once flags, etc.)
3. **Rewards**: What happens when triggered (stat buffs, gold, etc.)

### New Structure Format

```json
{
  "trigger": "on_enemy_death",
  "conditions": {
    "chance_percent": 100,
    "once_per_round": false,
    "once_per_combat": false,
    "max_triggers": null
  },
  "rewards": [
    {
      "type": "stat_buff",
      "target": "self",
      "stat": "defense",
      "value": 10,
      "value_type": "percentage_of_collected",
      "collect_stat": "defense",
      "duration": "permanent"
    }
  ]
}
```

### Trigger Types
- `on_enemy_death` - When an enemy dies
- `on_ally_death` - When an ally dies
- `per_second` - Every second during combat
- `per_round` - At the start of each round
- `on_ally_hp_below` - When ally HP drops below threshold
- `on_combat_start` - At combat start
- `on_combat_end` - At combat end

### Condition Types
- `chance_percent`: 0-100 chance to trigger
- `once_per_round`: Only once per round
- `once_per_combat`: Only once per combat
- `max_triggers`: Maximum number of triggers
- `cooldown_seconds`: Minimum time between triggers

### Reward Types

#### 1. Stat Buffs
```json
{
  "type": "stat_buff",
  "target": "self|team|trait",
  "stat": "attack|defense|hp|max_mana|attack_speed",
  "value": 10,
  "value_type": "flat|percentage|percentage_of_collected|percentage_of_base",
  "collect_stat": "defense|attack|hp" // only for percentage_of_collected
  "duration": "permanent|round_end|seconds",
  "duration_seconds": 5 // only if duration = "seconds"
}
```

#### 2. Resource Rewards
```json
{
  "type": "resource",
  "resource": "gold|xp|mana",
  "value": 5,
  "value_type": "flat"
}
```

#### 3. Healing/Regeneration
```json
{
  "type": "heal",
  "target": "self|team|trait",
  "value": 50,
  "value_type": "flat|percentage_of_max",
  "duration": "instant|seconds",
  "duration_seconds": 5
}
```

#### 4. Special Effects
```json
{
  "type": "special",
  "effect": "shield|lifesteal|stun|buff_amplifier",
  "value": 25,
  "duration": "round_end|seconds",
  "duration_seconds": 3
}
```

## Migration Examples

### Current Haker (kill_buff)
```json
// OLD
{
  "type": "on_enemy_death",
  "actions": [{
    "type": "kill_buff",
    "stat": "defense",
    "value": 10,
    "is_percentage": true,
    "collect_stat": "defense"
  }]
}

// NEW
{
  "trigger": "on_enemy_death",
  "conditions": {
    "chance_percent": 100
  },
  "rewards": [{
    "type": "stat_buff",
    "target": "self",
    "stat": "defense",
    "value": 10,
    "value_type": "percentage_of_collected",
    "collect_stat": "defense",
    "duration": "permanent"
  }]
}
```

### Current Denciak (reward with chance)
```json
// OLD
{
  "type": "on_ally_death",
  "actions": [{
    "type": "reward",
    "reward": "gold",
    "value": 1,
    "chance": 50
  }],
  "trigger_once": true
}

// NEW
{
  "trigger": "on_ally_death",
  "conditions": {
    "chance_percent": 50,
    "once_per_round": true
  },
  "rewards": [{
    "type": "resource",
    "resource": "gold",
    "value": 1,
    "value_type": "flat"
  }]
}
```

### Current Femboy (reward with duration)
```json
// OLD
{
  "type": "on_enemy_death",
  "actions": [{
    "type": "reward",
    "reward": "hp_regen",
    "target": "self",
    "value": 5,
    "is_percentage": true,
    "duration": 5
  }]
}

// NEW
{
  "trigger": "on_enemy_death",
  "conditions": {
    "chance_percent": 100
  },
  "rewards": [{
    "type": "heal",
    "target": "self",
    "value": 5,
    "value_type": "percentage_of_max",
    "duration": "seconds",
    "duration_seconds": 5
  }]
}
```

## Implementation Plan

1. **Create new effect processor** that handles the unified format
2. **Add comprehensive tests** for all reward types and conditions
3. **Migrate existing traits** to new format
4. **Update trait validation** to support both old and new formats during transition
5. **Add new reward types** as needed (shield, lifesteal, etc.)

## Benefits

- **Modular**: Easy to add new triggers, conditions, and rewards
- **Consistent**: All effects follow the same structure
- **Extensible**: New features don't require structural changes
- **Testable**: Each component can be tested independently
- **Maintainable**: Clear separation of concerns</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/MODULAR_TRAIT_SYSTEM_PLAN.md