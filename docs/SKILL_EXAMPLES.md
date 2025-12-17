# Skill Examples

This document provides examples of skill definitions for the Waffen Tactics game system.

## Skill Structure

Skills are defined as JSON objects with the following structure:

```json
{
  "name": "Skill Name",
  "description": "Brief description of what the skill does",
  "mana_cost": 50,
  "effects": [
    {
      "type": "effect_type",
      "target": "target_type",
      "param1": "value1",
      "param2": "value2"
    }
  ]
}
```

## Effect Types

### Damage
Deals direct damage to targets.

**Parameters:**
- `amount` (required): Amount of damage to deal
- `damage_type` (optional): Type of damage ("physical", "magical", etc.)

**Example:**
```json
{
  "type": "damage",
  "target": "single_enemy",
  "amount": 100,
  "damage_type": "magical"
}
```

### Heal
Restores HP to targets.

**Parameters:**
- `amount` (required): Amount of HP to restore

**Example:**
```json
{
  "type": "heal",
  "target": "ally_team",
  "amount": 150
}
```

### Shield
Grants temporary shield to targets.

**Parameters:**
- `amount` (required): Shield amount
- `duration` (required): Duration in seconds

**Example:**
```json
{
  "type": "shield",
  "target": "self",
  "amount": 200,
  "duration": 5
}
```

### Buff
Temporarily increases a stat.

**Parameters:**
- `stat` (required): Stat to buff ("attack", "defense", "attack_speed", etc.)
- `value` (required): Amount to increase
- `duration` (required): Duration in seconds
- `value_type` (optional): "flat" or "percentage"

**Example:**
```json
{
  "type": "buff",
  "target": "ally_team",
  "stat": "attack",
  "value": 20,
  "value_type": "percentage",
  "duration": 10
}
```

### Debuff
Temporarily decreases a stat.

**Parameters:**
- Same as buff but type is "debuff"

**Example:**
```json
{
  "type": "debuff",
  "target": "enemy_team",
  "stat": "defense",
  "value": 15,
  "duration": 8
}
```

### Stun
Disables targets for a duration.

**Parameters:**
- `duration` (required): Duration in seconds

**Example:**
```json
{
  "type": "stun",
  "target": "single_enemy",
  "duration": 2
}
```

### Damage Over Time
Deals damage periodically.

**Parameters:**
- `damage` (required): Damage per tick
- `duration` (required): Total duration
- `interval` (required): Time between ticks
- `damage_type` (optional): Type of damage

**Example:**
```json
{
  "type": "damage_over_time",
  "target": "enemy_front",
  "damage": 25,
  "duration": 5,
  "interval": 1,
  "damage_type": "poison"
}
```

### Delay
Delays execution of subsequent effects.

**Parameters:**
- `duration` (required): Delay in seconds

**Example:**
```json
{
  "type": "delay",
  "target": "self",
  "duration": 1
}
```

### Repeat
Repeats a set of effects multiple times.

**Parameters:**
- `count` (required): Number of repetitions
- `effects` (required): Array of effects to repeat

**Example:**
```json
{
  "type": "repeat",
  "target": "self",
  "count": 3,
  "effects": [
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 50
    },
    {
      "type": "delay",
      "target": "self",
      "duration": 0.5
    }
  ]
}
```

### Conditional
Executes effects based on a condition.

**Parameters:**
- `condition` (required): Condition object to check
- `effects` (required): Effects if condition is true
- `else_effects` (optional): Effects if condition is false

**Condition Types:**
- `health_percentage`: Check if target's HP is below a percentage
  - `threshold`: Percentage threshold (e.g., 50)
- `has_effect`: Check if target has a specific effect
  - `effect_type`: Type of effect to check for
- `stat_comparison`: Compare a stat value
  - `stat`: Stat name, `operator`: comparison operator, `value`: value to compare
- `random`: Random chance
  - `chance`: Percentage chance (0-100)

**Example:**
```json
{
  "type": "conditional",
  "target": "self",
  "condition": {
    "type": "health_percentage",
    "threshold": 50
  },
  "effects": [
    {
      "type": "heal",
      "target": "self",
      "amount": 250
    }
  ],
  "else_effects": [
    {
      "type": "buff",
      "target": "self",
      "stat": "attack",
      "value": 35,
      "value_type": "percentage",
      "duration": 7
    }
  ]
}
```

## Target Types

- `self`: The caster
- `single_enemy`: One random enemy (different target each time used)
- `single_enemy_persistent`: One enemy that persists across all effects in the same skill (same target for all effects)
- `enemy_team`: All enemies
- `enemy_front`: Front line enemies (first 3)
- `ally_team`: All allies
- `ally_front`: Front line allies (first 3)

## Example Skills

### Basic Examples

#### Stun and Damage Combo
A skill that stuns a single enemy and then deals damage to the same target.

```json
{
  "name": "Thunder Strike",
  "description": "Stuns an enemy and deals heavy damage",
  "mana_cost": 60,
  "effects": [
    {
      "type": "stun",
      "target": "single_enemy_persistent",
      "duration": 2
    },
    {
      "type": "damage",
      "target": "single_enemy_persistent",
      "amount": 150,
      "damage_type": "lightning"
    }
  ]
}
```

#### Area Heal with Buff
Heals all allies and buffs their defense.

```json
{
  "name": "Divine Protection",
  "description": "Heals allies and increases their defense",
  "mana_cost": 80,
  "effects": [
    {
      "type": "heal",
      "target": "ally_team",
      "amount": 200
    },
    {
      "type": "buff",
      "target": "ally_team",
      "stat": "defense",
      "value": 25,
      "value_type": "percentage",
      "duration": 10
    }
  ]
}
```

### Targeting Examples

#### Random vs Persistent Single Enemy Targeting

**Random Targeting (`single_enemy`)**: Each effect chooses a different random enemy.

```json
{
  "name": "Scatter Shot",
  "description": "Fires multiple shots at random enemies",
  "mana_cost": 60,
  "effects": [
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 80,
      "damage_type": "physical"
    },
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 80,
      "damage_type": "physical"
    },
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 80,
      "damage_type": "physical"
    }
  ]
}
```

**Persistent Targeting (`single_enemy_persistent`)**: All effects target the same enemy.

```json
{
  "name": "Focused Assault",
  "description": "Locks onto one enemy and unleashes multiple attacks",
  "mana_cost": 60,
  "effects": [
    {
      "type": "damage",
      "target": "single_enemy_persistent",
      "amount": 80,
      "damage_type": "physical"
    },
    {
      "type": "damage",
      "target": "single_enemy_persistent",
      "amount": 80,
      "damage_type": "physical"
    },
    {
      "type": "stun",
      "target": "single_enemy_persistent",
      "duration": 3
    }
  ]
}
```

### Complex Skill Examples

#### Sequential Damage with Delay
Damages a single enemy, waits, then damages the same target again.

```json
{
  "name": "Double Strike",
  "description": "Strikes an enemy twice with a delay between hits",
  "mana_cost": 70,
  "effects": [
    {
      "type": "damage",
      "target": "single_enemy_persistent",
      "amount": 100,
      "damage_type": "physical"
    },
    {
      "type": "delay",
      "target": "self",
      "duration": 1.0
    },
    {
      "type": "damage",
      "target": "single_enemy_persistent",
      "amount": 100,
      "damage_type": "physical"
    }
  ]
}
```

#### Offensive Combo with Self-Buff
Damages one enemy, buffs own defense, then damages multiple enemies.

```json
{
  "name": "Berserker Rage",
  "description": "Damages one enemy, gains defense, then strikes the front line",
  "mana_cost": 85,
  "effects": [
    {
      "type": "damage",
      "target": "single_enemy",
      "amount": 120,
      "damage_type": "physical"
    },
    {
      "type": "buff",
      "target": "self",
      "stat": "defense",
      "value": 50,
      "value_type": "flat",
      "duration": 8
    },
    {
      "type": "damage",
      "target": "enemy_front",
      "amount": 80,
      "damage_type": "physical"
    }
  ]
}
```

#### Multi-Phase Area Attack
Damages front line, delays, damages all enemies, delays, then stuns all enemies.

```json
{
  "name": "Cataclysm",
  "description": "Devastating area attack that builds up to stun all enemies",
  "mana_cost": 120,
  "effects": [
    {
      "type": "damage",
      "target": "enemy_front",
      "amount": 150,
      "damage_type": "magical"
    },
    {
      "type": "delay",
      "target": "self",
      "duration": 1.5
    },
    {
      "type": "damage",
      "target": "enemy_team",
      "amount": 100,
      "damage_type": "magical"
    },
    {
      "type": "delay",
      "target": "self",
      "duration": 1.0
    },
    {
      "type": "stun",
      "target": "enemy_team",
      "duration": 3
    }
  ]
}
```

#### Shield and Counter-Attack
Creates a shield, buffs attack, then damages enemies.

```json
{
  "name": "Fortress Counter",
  "description": "Shields self, increases attack power, then counter-attacks",
  "mana_cost": 90,
  "effects": [
    {
      "type": "shield",
      "target": "self",
      "amount": 250,
      "duration": 10
    },
    {
      "type": "buff",
      "target": "self",
      "stat": "attack",
      "value": 40,
      "value_type": "percentage",
      "duration": 8
    },
    {
      "type": "damage",
      "target": "enemy_front",
      "amount": 120,
      "damage_type": "physical"
    }
  ]
}
```

#### Poison DoT with Debuff
Applies damage over time and debuffs enemy defense.

```json
{
  "name": "Corrosive Poison",
  "description": "Poisons an enemy and weakens their defense over time",
  "mana_cost": 75,
  "effects": [
    {
      "type": "damage_over_time",
      "target": "single_enemy_persistent",
      "damage": 25,
      "duration": 8,
      "interval": 2.0,
      "damage_type": "poison"
    },
    {
      "type": "debuff",
      "target": "single_enemy_persistent",
      "stat": "defense",
      "value": 30,
      "value_type": "percentage",
      "duration": 8
    }
  ]
}
```

#### Repeat Attack Chain
Repeatedly damages the same enemy with delays between hits.

```json
{
  "name": "Rapid Fire",
  "description": "Fires multiple shots at one enemy",
  "mana_cost": 65,
  "effects": [
    {
      "type": "repeat",
      "target": "self",
      "count": 4,
      "effects": [
        {
          "type": "damage",
          "target": "single_enemy_persistent",
          "amount": 75,
          "damage_type": "physical"
        },
        {
          "type": "delay",
          "target": "self",
          "duration": 0.3
        }
      ]
    }
  ]
}
```

#### Team Buff and Heal
Buffs all allies' attack and heals them.

```json
{
  "name": "Battle Cry",
  "description": "Inspires allies with increased attack and healing",
  "mana_cost": 95,
  "effects": [
    {
      "type": "buff",
      "target": "ally_team",
      "stat": "attack",
      "value": 25,
      "value_type": "percentage",
      "duration": 12
    },
    {
      "type": "heal",
      "target": "ally_team",
      "amount": 150
    }
  ]
}
```

#### Conditional Emergency Heal
Heals self if HP is low, otherwise damages enemies.

```json
{
  "name": "Tactical Response",
  "description": "Heals if critically wounded, otherwise attacks",
  "mana_cost": 55,
  "effects": [
    {
      "type": "conditional",
      "target": "self",
      "condition": {
        "type": "health_percentage",
        "threshold": 50
      },
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "amount": 300
        },
        {
          "type": "shield",
          "target": "self",
          "amount": 200,
          "duration": 5
        }
      ],
      "else_effects": [
        {
          "type": "damage",
          "target": "enemy_front",
          "amount": 180,
          "damage_type": "physical"
        }
      ]
    }
  ]
}
```

#### Complex Multi-Phase Ultimate
A powerful ultimate that combines multiple effects: damages front, buffs self, damages all, stuns.

```json
{
  "name": "Apocalyptic Fury",
  "description": "Ultimate ability that devastates enemies with multiple phases",
  "mana_cost": 150,
  "effects": [
    {
      "type": "damage",
      "target": "enemy_front",
      "amount": 200,
      "damage_type": "magical"
    },
    {
      "type": "buff",
      "target": "self",
      "stat": "attack",
      "value": 50,
      "value_type": "percentage",
      "duration": 15
    },
    {
      "type": "delay",
      "target": "self",
      "duration": 1.0
    },
    {
      "type": "damage",
      "target": "enemy_team",
      "amount": 150,
      "damage_type": "magical"
    },
    {
      "type": "stun",
      "target": "enemy_team",
      "duration": 4
    }
  ]
}
```

#### Debuff and Follow-Up
Debuffs enemy attack speed, then damages them.

```json
{
  "name": "Slow Field",
  "description": "Slows down all enemies and damages them",
  "mana_cost": 70,
  "effects": [
    {
      "type": "debuff",
      "target": "enemy_team",
      "stat": "attack_speed",
      "value": 30,
      "value_type": "percentage",
      "duration": 8
    },
    {
      "type": "damage",
      "target": "enemy_team",
      "amount": 90,
      "damage_type": "magical"
    }
  ]
}
```

#### Self-Sustain Combo
Heals self, shields self, then buffs attack.

```json
{
  "name": "Guardian's Resolve",
  "description": "Restores health, shields, and increases attack power",
  "mana_cost": 100,
  "effects": [
    {
      "type": "heal",
      "target": "self",
      "amount": 250
    },
    {
      "type": "shield",
      "target": "self",
      "amount": 300,
      "duration": 8
    },
    {
      "type": "buff",
      "target": "self",
      "stat": "attack",
      "value": 35,
      "value_type": "percentage",
      "duration": 10
    }
  ]
}
```

#### Ally Support Ultimate
Heals all allies, buffs their stats, and shields them.

```json
{
  "name": "Divine Intervention",
  "description": "Powerful support ability that heals, buffs, and shields all allies",
  "mana_cost": 130,
  "effects": [
    {
      "type": "heal",
      "target": "ally_team",
      "amount": 300
    },
    {
      "type": "shield",
      "target": "ally_team",
      "amount": 200,
      "duration": 12
    },
    {
      "type": "buff",
      "target": "ally_team",
      "stat": "attack",
      "value": 30,
      "value_type": "percentage",
      "duration": 15
    },
    {
      "type": "buff",
      "target": "ally_team",
      "stat": "defense",
      "value": 40,
      "value_type": "percentage",
      "duration": 15
    }
  ]
}
```