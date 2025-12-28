# Modular Trait System Reference

## Core Structure

```json
{
  "modular_effects": [
    {
      "trigger": "trigger_type",
      "conditions": {
        "chance_percent": 100,
        "once_per_round": false,
        "max_triggers": null,
        "trigger_once": false,
        "threshold_percent": null
      },
      "rewards": [
        {
          "type": "reward_type",
          // ... reward-specific parameters
        }
      ]
    }
  ]
}
```

## Trigger Types

| Trigger | Description | Context Available |
|---------|-------------|-------------------|
| `on_enemy_death` | When an enemy unit dies | `current_unit`, `killed_unit`, `collected_stats` |
| `on_ally_death` | When an ally unit dies | `current_unit`, `dead_unit` |
| `per_second` | Every second during combat | `current_unit`, `all_units` |
| `per_round` | At the start of each round | `current_unit`, `all_units` |
| `on_ally_hp_below` | When ally HP drops below threshold | `current_unit`, `low_hp_unit`, `current_hp_percent` |
| `per_trait` | Bonus per active synergy | `current_unit`, `active_trait_count` |
| `on_win` | After winning a round | `current_unit`, `all_units` |
| `on_loss` | After losing a round | `current_unit`, `all_units` |

## Condition Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chance_percent` | number | 100 | 0-100% chance to trigger |
| `once_per_round` | boolean | false | Only once per round |
| `max_triggers` | number/null | null | Maximum number of triggers |
| `trigger_once` | boolean | false | Only once ever (per combat) |
| `threshold_percent` | number/null | null | HP threshold for `on_ally_hp_below` |

## Reward Types & Parameters

### 1. `stat_buff` - Stat Bonuses
```json
{
  "type": "stat_buff",
  "stat": "attack|defense|hp|attack_speed|max_mana|lifesteal",
  "value": 10,
  "value_type": "flat|percentage_of_max|percentage_of_collected|per_active_trait",
  "collect_stat": "defense|attack|hp",  // only for percentage_of_collected
  "duration": "permanent|round_end|seconds",
  "duration_seconds": 5  // only if duration = "seconds"
}
```

### 2. `resource` - Gold/XP/Mana Rewards
```json
{
  "type": "resource",
  "resource": "gold|xp|mana",
  "value": 5,
  "value_type": "flat"
}
```

### 3. `healing` - HP Regeneration
```json
{
  "type": "healing",
  "value": 50,
  "value_type": "flat|percentage_of_max",
  "duration": "instant|seconds",
  "duration_seconds": 5
}
```

### 4. `enemy_debuff` - Debuff Enemy Team
```json
{
  "type": "enemy_debuff",
  "stat": "attack|defense|attack_speed",
  "value": 15
}
```

### 5. `mana_regen` - Mana Regeneration
```json
{
  "type": "mana_regen",
  "value": 3
}
```

### 6. `buff_amplifier` - Multiply Other Buffs
```json
{
  "type": "buff_amplifier",
  "multiplier": 2.0
}
```

### 7. `targeting_preference` - Change Targeting
```json
{
  "type": "targeting_preference",
  "target_preference": "backline|frontline|lowest_hp"
}
```

### 8. `reroll_chance` - Free Shop Reroll
```json
{
  "type": "reroll_chance",
  "chance_percent": 30
}
```

### 9. `dynamic_scaling` - Scaling Per Wins/Losses
```json
{
  "type": "dynamic_scaling",
  "atk_per_win": 1,
  "def_per_win": 1,
  "hp_percent_per_win": 1,
  "as_per_win": 0.01,
  "percent_per_loss": 5
}
```

### 10. `special` - Special Effects (HP Regen, etc.)
```json
{
  "type": "special",
  "value": 5  // HP regen percentage
}
```

## Value Types

| Value Type | Description | Example |
|------------|-------------|---------|
| `flat` | Fixed numeric value | `+10 attack` |
| `percentage_of_max` | Percentage of unit's base stat | `+25% attack speed` |
| `percentage_of_collected` | Percentage of killed enemy's stat | `+10% of killed unit's defense` |
| `per_active_trait` | Multiplied by number of active synergies | `+4 attack per synergy` |

## Duration Types

| Duration | Description |
|----------|-------------|
| `permanent` | Lasts until end of combat |
| `round_end` | Expires at end of current round |
| `seconds` | Expires after specified seconds |
| `instant` | Applied immediately (for healing) |

## Complete Examples

### Srebrna Gwardia (Per Second Defense)
```json
{
  "trigger": "per_second",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "defense",
      "value": 3
    }
  ]
}
```

### Haker (Percentage of Killed Enemy's Defense)
```json
{
  "trigger": "on_enemy_death",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "defense",
      "value": 10,
      "value_type": "percentage_of_collected",
      "collect_stat": "defense"
    }
  ]
}
```

### Denciak (Gold on Ally Death with Chance)
```json
{
  "trigger": "on_ally_death",
  "conditions": {
    "trigger_once": true
  },
  "rewards": [
    {
      "type": "resource",
      "resource": "gold",
      "value": 1
    }
  ]
}
```

### Femboy (HP Regen After Kill)
```json
{
  "trigger": "on_enemy_death",
  "conditions": {},
  "rewards": [
    {
      "type": "special",
      "value": 5
    }
  ]
}
```

### Szachista (Per Active Trait Bonus)
```json
{
  "trigger": "per_trait",
  "conditions": {},
  "rewards": [
    {
      "type": "stat_buff",
      "stat": "attack",
      "value": 4,
      "value_type": "per_active_trait"
    },
    {
      "type": "stat_buff",
      "stat": "hp",
      "value": 4,
      "value_type": "per_active_trait"
    }
  ]
}
```

### XN Yakuza (Scaling Per Win)
```json
{
  "trigger": "on_win",
  "conditions": {},
  "rewards": [
    {
      "type": "dynamic_scaling",
      "atk_per_win": 1,
      "def_per_win": 1,
      "hp_percent_per_win": 1,
      "as_per_win": 0.01
    }
  ]
}
```

### Wygnaniec (Conditional Healing)
```json
{
  "trigger": "on_ally_hp_below",
  "conditions": {
    "trigger_once": true,
    "threshold_percent": 30
  },
  "rewards": [
    {
      "type": "healing",
      "value": 50,
      "value_type": "percentage_of_max"
    }
  ]
}
```

## Quick Reference: All Reward Types

| Reward Type | Required Params | Optional Params | Description |
|-------------|-----------------|-----------------|-------------|
| `stat_buff` | `stat`, `value` | `value_type`, `collect_stat`, `duration`, `duration_seconds` | Stat bonuses (attack, defense, hp, etc.) |
| `resource` | `resource`, `value` | `value_type` | Gold/XP/Mana rewards |
| `healing` | `value` | `value_type`, `duration`, `duration_seconds` | HP regeneration |
| `enemy_debuff` | `stat`, `value` | - | Debuff enemy team stats |
| `mana_regen` | `value` | - | Increased mana regeneration |
| `buff_amplifier` | `multiplier` | - | Multiply other buffs |
| `targeting_preference` | `target_preference` | - | Change targeting behavior |
| `reroll_chance` | `chance_percent` | - | Free shop reroll chance |
| `dynamic_scaling` | - | `atk_per_win`, `def_per_win`, `hp_percent_per_win`, `as_per_win`, `percent_per_loss` | Scaling bonuses per wins/losses |
| `special` | `value` | - | Special effects (HP regen, etc.) |

## Quick Reference: All Trigger Types

| Trigger | When | Common Use Cases |
|---------|------|------------------|
| `on_enemy_death` | Enemy unit dies | Kill-based buffs, stat stealing |
| `on_ally_death` | Ally unit dies | Gold rewards, resurrection effects |
| `per_second` | Every combat second | Continuous buffs (defense per second) |
| `per_round` | Round start | Round-based scaling (HP per round) |
| `on_ally_hp_below` | Ally HP < threshold | Emergency healing |
| `per_trait` | Per active synergy | Chess master bonuses |
| `on_win` | Round victory | Victory scaling (Yakuza) |
| `on_loss` | Round defeat | Loss-based scaling (Monter) |</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/MODULAR_TRAIT_REFERENCE.md