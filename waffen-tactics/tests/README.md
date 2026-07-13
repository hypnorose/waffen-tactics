# Comprehensive System Tests

This test suite provides comprehensive coverage for the Traits System and Combat mechanics. Skill-focused cases are kept as skipped legacy coverage because the current ruleset has skills disabled.

## Running Tests

From the project root directory:

```bash
# Run all comprehensive tests
pytest waffen-tactics/tests/test_comprehensive_system.py

# Run specific test classes
pytest waffen-tactics/tests/test_comprehensive_system.py::TestTraitsSystem
pytest waffen-tactics/tests/test_comprehensive_system.py::TestSkillsSystem
pytest waffen-tactics/tests/test_comprehensive_system.py::TestCombatSystem

# Run individual tests
pytest waffen-tactics/tests/test_comprehensive_system.py::TestCombatSystem::test_no_double_deaths_from_skills -v
```

## Test Coverage

### Traits System (`TestTraitsSystem`)
- **Death-based effects**: `on_enemy_death`, `on_ally_death` gold rewards
- **Per-second buffs**: Defense, attack, HP regeneration over time
- **Per-round buffs**: HP scaling based on round number
- **Mana regeneration**: Passive mana gain effects

### Skills System (`TestSkillsSystem`)
- Skipped legacy coverage kept only for reference while skills remain disabled.

### Combat System (`TestCombatSystem`)
- **Death handling**: No double death events from attacks or skills
- **Trait integration**: Death-based effects trigger from combat deaths
- **Mana accumulation**: Full mana still grants the extra basic attack
- **Event ordering**: Combat events in chronological order

## Key Features Tested

### Preventing Regressions
- **Double deaths**: Ensures units die exactly once, regardless of attack/skill source
- **Missing trait effects**: Verifies `on_enemy_death`, `on_ally_death` trigger properly
- **Skill event format**: Correct field names for UI integration
- **Combat flow**: Proper event sequencing and state management

### Edge Cases Covered
- Attack kills vs legacy skill-kill scenarios
- Trait effects on both sides of combat
- Mana management and regeneration
- Event callback correctness
- Combat termination conditions

## Adding New Tests

When adding new features to traits, skills, or combat:

1. Add corresponding test methods to the appropriate test class
2. Follow the existing patterns for setup and assertions
3. Ensure tests are isolated and don't depend on external state
4. Test both success and failure scenarios
5. Verify event callbacks work correctly
6. Keep skill-specific coverage skipped unless the ruleset changes

## Test Structure

```
test_comprehensive_system.py
├── TestTraitsSystem
│   ├── test_on_enemy_death_gold_reward
│   ├── test_on_ally_death_gold_reward
│   ├── test_per_second_buff_defense
│   ├── test_per_round_buff_hp
│   └── test_mana_regen_effect
├── TestSkillsSystem
│   ├── test_skill_execution_deducts_mana
│   ├── test_skill_execution_insufficient_mana
│   └── test_skill_cast_event_format
└── TestCombatSystem
    ├── test_no_double_deaths_from_attacks
    ├── test_no_double_deaths_from_skills
    ├── test_skill_kills_trigger_trait_effects
    ├── test_mana_accumulation_and_skill_casting
    └── test_combat_event_ordering
```

Run these tests regularly to catch regressions early in development!</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/waffen-tactics/tests/README.md
