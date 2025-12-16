# Large Python Files Refactoring Proposals

This document analyzes the largest Python files in the Waffen Tactics codebase and proposes refactoring strategies to improve maintainability, readability, and modularity. The focus is on the main backend in `waffen-tactics/` directory, with secondary attention to web API routes.

## File Analysis Summary

Based on line count analysis, here are the largest Python files in the main backend (`waffen-tactics/`):

| File | Lines | Location | Description |
|------|-------|----------|-------------|
| `combat_effect_processor.py` | 541 | `waffen-tactics/src/waffen_tactics/services/` | Combat effect processing logic |
| `database.py` | 348 | `waffen-tactics/src/waffen_tactics/services/` | Database operations |
| `combat_shared_old.py` | 322 | `waffen-tactics/src/waffen_tactics/services/` | Legacy combat shared logic |
| `combat_simulator.py` | 321 | `waffen-tactics/src/waffen_tactics/services/` | Combat simulation engine |
| `unit_manager.py` | 311 | `waffen-tactics/src/waffen_tactics/services/` | Unit management logic |
| `synergy.py` | 262 | `waffen-tactics/src/waffen_tactics/services/` | Synergy calculation engine |

Additional large files in web API layer (`waffen-tactics-web/backend/routes/`):
- `game_combat.py` (633 lines) - Combat route handlers
- `admin.py` (495 lines) - Admin panel API routes

## Detailed Refactoring Proposals for Main Backend

### 1. `combat_effect_processor.py` (541 lines)

**Current Structure:**
- Monolithic class handling all combat effects
- Complex conditional logic for different effect types
- Hard to extend with new effects

**Refactoring Strategy:**

#### Strategy Pattern Implementation
- Create base `EffectProcessor` abstract class
- Implement specific processors for each effect type:
  - `DamageEffectProcessor`
  - `BuffEffectProcessor`
  - `HealEffectProcessor`
  - `StatusEffectProcessor`

**Proposed Structure:**
```
waffen-tactics/src/waffen_tactics/services/effects/
├── base_effect_processor.py
├── damage_processor.py
├── buff_processor.py
├── heal_processor.py
└── status_processor.py

waffen-tactics/src/waffen_tactics/services/
└── combat_effect_processor.py  # Orchestrator (50-100 lines)
```

#### Factory Pattern for Effect Creation
- `EffectProcessorFactory` to instantiate correct processor
- Registry pattern for dynamic effect registration

**Benefits:**
- Easy to add new effect types
- Better testability
- Reduced complexity in main processor

### 2. `database.py` (348 lines)

**Current Structure:**
- Large database service class
- Mixed async and sync operations
- Multiple responsibilities: connections, queries, data transformation

**Refactoring Strategy:**

#### Repository Pattern
- Create repository classes for each entity:
  - `PlayerRepository`
  - `GameRepository`
  - `LeaderboardRepository`

**Proposed Structure:**
```
waffen-tactics/src/waffen_tactics/services/database/
├── base_repository.py
├── player_repository.py
├── game_repository.py
├── leaderboard_repository.py
└── database_manager.py  # Connection and transaction management
```

#### Query Builders
- Extract complex query building logic
- Create `QueryBuilder` classes for different query types

**Benefits:**
- Better separation of data access logic
- Easier testing with mock repositories
- Improved code reusability

### 3. `combat_simulator.py` (321 lines)

**Current Structure:**
- Complex combat simulation logic
- Mixed battle mechanics and result calculation
- Hard to understand battle flow

**Refactoring Strategy:**

#### Component-Based Architecture
- `BattleEngine` - Main simulation orchestrator
- `UnitCombatant` - Individual unit behavior
- `BattleState` - Battle state management
- `DamageCalculator` - Damage computation logic

**Proposed Structure:**
```
waffen-tactics/src/waffen_tactics/services/combat/
├── battle_engine.py
├── unit_combatant.py
├── battle_state.py
├── damage_calculator.py
└── combat_simulator.py  # Simplified orchestrator
```

#### Event-Driven Approach
- Implement combat events system
- Allow plugins/extensions for custom mechanics

**Benefits:**
- Modular combat system
- Easier to balance and modify
- Better performance profiling

### 4. `unit_manager.py` (311 lines)

**Current Structure:**
- Unit creation, modification, and management
- Mixed data access and business logic
- Complex unit upgrade logic

**Refactoring Strategy:**

#### Domain-Driven Design
- `Unit` entity with business logic
- `UnitFactory` for unit creation
- `UnitUpgrader` for upgrade mechanics
- `UnitValidator` for unit state validation

**Proposed Structure:**
```
waffen-tactics/src/waffen_tactics/models/
├── unit.py
└── unit_instance.py

waffen-tactics/src/waffen_tactics/services/
├── unit_factory.py
├── unit_upgrader.py
├── unit_validator.py
└── unit_manager.py  # Coordinator
```

**Benefits:**
- Clear domain boundaries
- Easier unit balancing
- Better test coverage

### 5. `synergy.py` (262 lines)

**Current Structure:**
- Synergy calculation and application logic
- Mixed trait processing and stat modification
- Complex conditional logic for different synergy types

**Refactoring Strategy:**

#### Modular Synergy System
- `SynergyCalculator` - Core calculation logic
- `TraitProcessor` - Individual trait processing
- `StatModifier` - Stat modification logic
- `SynergyValidator` - Synergy validation

**Proposed Structure:**
```
waffen-tactics/src/waffen_tactics/services/synergy/
├── synergy_calculator.py
├── trait_processor.py
├── stat_modifier.py
├── synergy_validator.py
└── synergy_engine.py  # Main orchestrator
```

**Benefits:**
- Easier to add new synergies
- Better separation of concerns
- Improved maintainability

### 6. `combat_shared_old.py` (322 lines) - LEGACY

**Recommendation:**
- **Archive/Remove** - This appears to be legacy code
- Migrate any still-used functionality to new combat modules
- Keep as reference during transition period

## Web API Layer Refactoring

### 1. `game_combat.py` (633 lines) - Web Routes

**Refactoring Strategy:**

#### Extract Service Layer
- Move combat business logic to main backend services
- Keep routes thin, focused only on HTTP handling

**Proposed Structure:**
```
waffen-tactics-web/backend/routes/
└── game_combat.py  # Thin route handlers (100-150 lines)

waffen-tactics-web/backend/services/
├── combat_service.py  # Web-specific combat orchestration
└── combat_streaming.py  # SSE streaming logic
```

### 2. `admin.py` (495 lines) - Web Routes

**Refactoring Strategy:**

#### Split by Domain
- `admin_user_management.py` - User-related admin functions
- `admin_game_stats.py` - Game statistics and analytics
- `admin_system_tools.py` - System maintenance tools

**Proposed Structure:**
```
waffen-tactics-web/backend/routes/admin/
├── __init__.py
├── user_management.py
├── game_statistics.py
├── system_tools.py
└── base_admin.py  # Common admin utilities
```

## Implementation Priority

### High Priority (Core Backend)
1. `combat_effect_processor.py` - Strategy pattern
2. `database.py` - Repository pattern
3. `combat_simulator.py` - Component architecture

### Medium Priority (Supporting Services)
1. `unit_manager.py` - Domain modeling
2. `synergy.py` - Modular synergy system
3. `combat_shared_old.py` - Cleanup legacy code

### Low Priority (Web Layer)
1. `game_combat.py` - Extract service layer
2. `admin.py` - Split by domain

## Architecture Principles

### Main Backend (`waffen-tactics/`)
- **Domain-Driven Design**: Clear separation between domain logic and infrastructure
- **Dependency Injection**: Services should be injectable for testing
- **SOLID Principles**: Single responsibility, open/closed, etc.
- **Async/Await**: Proper async patterns throughout

### Web API Layer (`waffen-tactics-web/backend/`)
- **Thin Controllers**: Routes should only handle HTTP concerns
- **Service Layer**: Business logic in dedicated services
- **Error Handling**: Centralized error handling and logging
- **API Versioning**: Support for future API evolution

## Risk Assessment

### Technical Risks
- Breaking changes during refactoring
- Performance impact of additional abstractions
- Increased complexity in some areas

### Mitigation Strategies
- Refactor incrementally with feature flags
- Comprehensive testing before deployment
- Performance monitoring during changes
- Documentation updates for new structure

## Success Metrics

### Code Quality
- Average file size reduction by 60%
- Improved test coverage (>80%)
- Reduced cyclomatic complexity

### Developer Experience
- Faster feature development
- Easier debugging and maintenance
- Better code navigation

### System Performance
- Maintained or improved response times
- Reduced memory usage
- Better error handling

## Conclusion

The proposed refactoring will significantly improve the codebase maintainability and scalability. Focus on the main backend (`waffen-tactics/`) first, as it contains the core business logic. The web API layer should be refactored to use the main backend services, creating a clean separation between web concerns and domain logic.