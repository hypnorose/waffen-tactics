# Skill System Design Plan

## Overview
This document outlines the design and implementation plan for a comprehensive, extensible skill system for the Waffen Tactics game. The system will allow units to have complex skills defined in `units.json` that can combine multiple effects like damage, healing, buffs, debuffs, and timing controls.

## Goals
- **Extensibility**: Easy to add new skill effects without major code changes
- **Flexibility**: Support for complex skill combinations and timing
- **Maintainability**: Clean separation of concerns with dedicated modules
- **Performance**: Efficient execution during combat
- **Data-Driven**: Skills defined in JSON for easy balancing

## Architecture

### Core Components
1. **Skill Model** (`models/skill.py`)
   - Data structures for skills and effects
   - Validation and parsing logic

2. **Skill Parser** (`services/skill_parser.py`)
   - Parse skill definitions from JSON
   - Validate skill structure
   - Convert to executable format

3. **Skill Executor** (`services/skill_executor.py`)
   - Execute skills during combat
   - Handle timing and sequencing
   - Apply effects to targets

4. **Effect Handlers** (`services/effects/`)
   - Individual effect implementations
   - Damage, healing, buffs, etc.
   - Modular for easy extension

5. **Combat Integration** (`services/combat_service.py`)
   - Trigger skill execution
   - Pass context to skill system

### Data Flow
```
units.json → Skill Parser → Skill Executor → Effect Handlers → Combat State Updates
```

## Skill Definition Format

### Basic Structure
```json
{
  "skill": {
    "name": "Fire Storm",
    "description": "Deals damage to all enemies with delayed waves",
    "mana_cost": 100,
    "effects": [
      {
        "type": "delay",
        "duration": 0.5
      },
      {
        "type": "damage",
        "target": "enemy_team",
        "amount": 50,
        "damage_type": "fire"
      },
      {
        "type": "delay",
        "duration": 1.0
      },
      {
        "type": "damage",
        "target": "enemy_team",
        "amount": 75,
        "damage_type": "fire"
      }
    ]
  }
}
```

### Effect Types

#### Core Effects
- **damage**: Deal damage to targets
- **heal**: Restore HP to targets
- **shield**: Grant temporary damage reduction
- **buff**: Temporary stat increase
- **debuff**: Temporary stat decrease
- **stun**: Prevent actions for duration

#### Control Effects
- **delay**: Wait before next effect
- **repeat**: Repeat effects multiple times
- **conditional**: Execute based on conditions

#### Targeting
- **single_enemy**: One random enemy
- **enemy_team**: All enemies
- **enemy_front**: Front line enemies
- **ally_team**: All allies
- **self**: The caster

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create skill models and data structures
2. Implement basic skill parser
3. Set up effect handler framework
4. Integrate with combat system

### Phase 2: Basic Effects
1. Implement damage and heal effects
2. Add targeting system
3. Create delay mechanism
4. Add basic buffs/debuffs

### Phase 3: Advanced Effects
1. Implement stun and shield effects
2. Add conditional effects
3. Create repeat functionality
4. Add damage over time

### Phase 4: Optimization & Polish
1. Performance optimization
2. Error handling and validation
3. Unit tests and integration tests
4. Documentation and examples

## File Structure
```
waffen-tactics/src/waffen_tactics/
├── models/
│   ├── skill.py              # Skill and Effect data models
│   └── effect.py             # Effect-specific models
├── services/
│   ├── skill_parser.py       # Parse skills from JSON
│   ├── skill_executor.py     # Execute skills in combat
│   └── effects/
│       ├── __init__.py
│       ├── damage.py         # Damage effect handler
│       ├── heal.py           # Heal effect handler
│       ├── buff.py           # Buff effect handler
│       ├── delay.py          # Delay effect handler
│       └── ...
└── combat/
    └── skill_integration.py  # Combat system integration
```

## Key Design Decisions

### Effect Handler Pattern
Each effect type has a dedicated handler class with:
- `validate()`: Check effect parameters
- `execute()`: Apply the effect
- `get_targets()`: Determine affected units

### Timing System
- Effects execute sequentially by default
- `delay` effect pauses execution
- Combat time advances during delays
- Async execution for complex timing

### Targeting System
- Flexible target selection
- Support for random, positional, and conditional targeting
- Target validation and fallbacks

### Extensibility
- New effects added by creating new handler classes
- Automatic registration via decorators
- JSON schema validation for effect definitions

## Integration Points

### With Combat System
- Skills triggered when unit mana reaches threshold
- Skill execution pauses combat temporarily
- Effects modify combat state directly
- Events logged for frontend streaming

### With Unit System
- Skills loaded from units.json during data loading
- Skill availability checked during combat
- Mana costs deducted on cast

### With Effect System
- Skills use same buff/debuff system as traits
- Temporary effects have duration
- Stack with existing effects

## Testing Strategy

### Unit Tests
- Individual effect handlers
- Skill parsing and validation
- Targeting logic
- Timing mechanisms

### Integration Tests
- Full skill execution in combat
- Multiple effects in sequence
- Edge cases and error conditions

### Performance Tests
- Skill execution time
- Memory usage with many effects
- Combat simulation with skills

## Risk Mitigation

### Backward Compatibility
- Existing units without skills continue to work
- Graceful degradation for invalid skill definitions

### Error Handling
- Validate skills at load time
- Runtime error recovery
- Detailed logging for debugging

### Performance
- Lazy loading of skill handlers
- Efficient target selection
- Minimal combat interruption

## Success Metrics
- All planned effect types implemented
- Skills execute correctly in combat
- System handles complex skill combinations
- Performance impact < 10% on combat speed
- Easy to add new effects without code changes</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/notes/skill_system_design.md