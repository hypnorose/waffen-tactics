# Option 1: Unified Structure (Recommended)
```json
{
  "trigger": "on_enemy_death",
  "conditions": {
    "chance_percent": 100,
    "once_per_round": false
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

# Option 2: Flat Structure (Simpler)
```json
{
  "trigger": "on_enemy_death",
  "chance_percent": 100,
  "once_per_round": false,
  "reward_type": "stat_buff",
  "target": "self",
  "stat": "defense",
  "value": 10,
  "value_type": "percentage_of_collected",
  "collect_stat": "defense",
  "duration": "permanent"
}
```

# Option 3: Action-Based (Current evolution)
```json
{
  "trigger": "on_enemy_death",
  "conditions": {
    "chance_percent": 100,
    "once_per_round": false
  },
  "actions": [{
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

# Option 4: Event-Driven (Most flexible)
```json
{
  "event": "enemy_death",
  "conditions": [
    {"type": "chance", "value": 100},
    {"type": "once_per_round", "value": false}
  ],
  "effects": [{
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

**I recommend Option 1** because:
- Clear separation of trigger/conditions/rewards
- Easy to extend with new condition types
- Rewards are self-contained objects
- Most readable and maintainable

Let me implement Option 1 with comprehensive tests.</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/MODULAR_SYSTEM_OPTIONS.md