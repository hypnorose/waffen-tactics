# Combat, Units & Stats Code Refactoring Analysis

This document analyzes the current implementation of combat system, units, and statistics handling in the Waffen Tactics codebase, identifying violations of DRY, SOLID principles, and areas requiring refactoring.

## Current Architecture Overview

The combat system spans multiple files:
- `combat_effect_processor.py` - Main effect processing logic
- `combat_unit.py` - Unit representation during combat
- `game_combat.py` (web layer) - Combat orchestration and result application
- Various model files for units and stats

## Major Issues Identified

### 1. Single Responsibility Principle (SRP) Violations

#### `combat_effect_processor.py::_apply_stat_buff()`
**Problem**: This method handles stat buffing for multiple different stats (attack, defense, hp, attack_speed, mana_regen, lifesteal, damage_reduction, hp_regen_per_sec) in one monolithic function.

**Issues**:
- 150+ lines of conditional logic
- Mixed responsibilities: stat calculation, recipient finding, logging, event callbacks
- Hard to extend with new stats
- Difficult to test individual stat behaviors

**Refactoring Needed**:
- Extract stat-specific handlers into separate classes/methods
- Use Strategy pattern for different stat types
- Create `StatBuffProcessor` interface with implementations for each stat

#### `combat_effect_processor.py` Overall
**Problem**: The entire class mixes death processing, reward application, and stat buffing.

**Issues**:
- Too many responsibilities in one class
- Tight coupling between different effect types

**Refactoring Needed**:
- Split into `DeathEffectProcessor`, `RewardProcessor`, `StatBuffProcessor`
- Use composition over inheritance

### 2. Don't Repeat Yourself (DRY) Violations

#### Stat Calculation Logic Duplication
**Problem**: Similar stat calculation patterns repeated across multiple methods.

**Examples**:
```python
# In _apply_stat_buff for attack
if is_pct:
    add = int(unit.attack * (val / 100.0))
else:
    add = int(val)

# In _apply_stat_buff for defense
if is_pct:
    base_add = int(unit.defense * (val / 100.0))
else:
    base_add = int(val)

# Similar patterns for hp, attack_speed, etc.
```

**Issues**:
- Same percentage calculation logic repeated 8+ times
- Same buff amplifier logic repeated
- Same recipient finding logic repeated

**Refactoring Needed**:
- Create `StatCalculator` utility class
- Extract common buff application logic
- Use data-driven approach for stat definitions

#### Recipient Finding Duplication
**Problem**: Logic for finding buff recipients (self, team, trait, board) is duplicated.

**Issues**:
- Same conditional logic in multiple places
- Hardcoded target types

**Refactoring Needed**:
- Create `RecipientResolver` class
- Use strategy pattern for different targeting modes

### 3. Open/Closed Principle (OCP) Violations

#### Hardcoded Stat Types
**Problem**: New stats require code changes in multiple places.

**Examples**:
- `_apply_stat_buff()` has explicit if/elif chains for each stat
- `CombatUnit` has hardcoded stat fields
- Effect processing has hardcoded stat handling

**Issues**:
- Adding new stats requires touching multiple files
- Risk of missing updates in some places

**Refactoring Needed**:
- Make stats data-driven with configuration
- Use reflection/polymorphism for stat handling
- Create `Stat` base class with specific implementations

#### Effect Type Hardcoding
**Problem**: Effect types are hardcoded strings throughout the codebase.

**Examples**:
```python
if eff.get('type') == 'on_enemy_death':
if action.get('type') == 'kill_buff':
```

**Issues**:
- Typos in strings can break functionality
- No compile-time checking
- Hard to discover all effect types

**Refactoring Needed**:
- Use enums or constants for effect types
- Create effect type registry
- Use polymorphism for effect handlers

### 4. Dependency Inversion Principle (DIP) Violations

#### Tight Coupling to CombatUnit
**Problem**: Many classes directly depend on `CombatUnit` implementation details.

**Examples**:
- Direct access to `unit.effects`, `unit.attack`, etc.
- Hardcoded assumptions about CombatUnit structure

**Issues**:
- Hard to test in isolation
- Changes to CombatUnit break multiple classes

**Refactoring Needed**:
- Create interfaces for unit interactions
- Use dependency injection for stat access
- Abstract unit operations behind interfaces

### 5. Interface Segregation Principle (ISP) Violations

#### CombatUnit Interface Bloat
**Problem**: `CombatUnit` has too many responsibilities and fields.

**Current fields**:
- Combat stats (hp, attack, defense, etc.)
- Effects and synergies
- Mana system
- Position and ID
- Collected stats
- Various caches and accumulators

**Issues**:
- Single class doing too many things
- Hard to understand and maintain

**Refactoring Needed**:
- Split into `CombatStats`, `EffectContainer`, `ManaSystem`, etc.
- Use composition
- Create focused interfaces for different aspects

## Specific Refactoring Proposals

### Phase 1: Immediate Improvements

#### 1. Extract Stat Calculator
```python
class StatCalculator:
    @staticmethod
    def calculate_buff(base_value: float, buff_value: float, is_percentage: bool, amplifier: float = 1.0) -> float:
        if is_percentage:
            return base_value * (buff_value / 100.0) * amplifier
        return buff_value * amplifier
```

#### 2. Create Stat Buff Handlers
```python
class StatBuffHandler(ABC):
    @abstractmethod
    def apply_buff(self, unit: 'CombatUnit', value: float, is_percentage: bool) -> None:
        pass

class AttackBuffHandler(StatBuffHandler):
    def apply_buff(self, unit: 'CombatUnit', value: float, is_percentage: bool) -> None:
        # Implementation
```

#### 3. Refactor _apply_stat_buff
Replace monolithic method with:
```python
def _apply_stat_buff(self, unit, effect, hp_list, unit_idx, time, log, event_callback, side, attacking_team, defending_team, attacking_hp, defending_hp):
    stat = effect.get('stat')
    handler = self.stat_handlers.get(stat)
    if handler:
        # Common logic for recipients, amplifiers, etc.
        # Then delegate to specific handler
        handler.apply_buff(...)
```

### Phase 2: Major Architectural Changes

#### 1. Effect System Redesign
- Create `Effect` base class with `process()` method
- Specific effect classes: `OnEnemyDeathEffect`, `StatBuffEffect`, etc.
- Effect registry/factory for instantiation

#### 2. Stat System Redesign
- Create `Stat` interface with `apply_buff()`, `get_value()` methods
- Specific stat classes: `AttackStat`, `DefenseStat`, etc.
- Stats registry for dynamic stat management

#### 3. Unit Composition
```python
@dataclass
class CombatUnit:
    stats: StatContainer
    effects: EffectContainer
    mana_system: ManaSystem
    position_system: PositionSystem
    # etc.
```

### Phase 3: Testing and Validation

#### 1. Unit Tests
- Test each stat buff handler in isolation
- Mock dependencies for effect processing
- Test effect combinations

#### 2. Integration Tests
- Test full combat scenarios
- Validate stat calculations end-to-end

## Benefits of Refactoring

### Maintainability
- Easier to add new stats and effects
- Clear separation of concerns
- Reduced coupling

### Testability
- Isolated unit tests for each component
- Easier mocking of dependencies

### Extensibility
- Plugin-like architecture for new features
- Data-driven stat and effect definitions

### Performance
- Reduced code duplication
- More efficient stat calculations
- Better memory usage with composition

## Implementation Priority

### High Priority (Breaking Changes)
1. Extract stat calculation utilities
2. Create stat buff handler interfaces
3. Refactor _apply_stat_buff method

### Medium Priority (Incremental)
1. Implement effect type enums/constants
2. Create recipient resolver
3. Split CombatUnit into composed parts

### Low Priority (Future Enhancements)
1. Full effect system redesign
2. Stat registry system
3. Plugin architecture for custom effects

## Risk Assessment

### Technical Risks
- Large refactoring may introduce bugs
- Performance impact during transition
- Breaking changes to existing APIs

### Mitigation Strategies
- Implement changes incrementally
- Comprehensive test coverage before/after
- Feature flags for gradual rollout
- Performance monitoring

### Business Risks
- Combat balance may be affected
- New features delayed during refactoring

### Mitigation Strategies
- Preserve existing behavior during refactoring
- Extensive playtesting after changes
- Rollback plan for critical issues

## Conclusion

The current combat system, while functional, suffers from significant architectural issues that make it hard to maintain and extend. The proposed refactoring will create a more modular, testable, and extensible system that follows SOLID principles and DRY practices.

Priority should be given to immediate improvements that can be implemented without major breaking changes, followed by larger architectural improvements.</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/notes/combat_units_stats_refactoring_analysis.md