# Backend Refactoring Plan: Separating Business Logic from Flask

## Overview
The current backend tests are failing because business logic is tightly coupled with Flask-specific code (`request`, `jsonify`, etc.). This makes testing difficult and violates separation of concerns.

## Goal
Separate business logic into pure functions that can be tested independently, while keeping Flask routes as thin HTTP adapters.

## Current Issues
- Routes contain business logic mixed with HTTP handling
- Tests can't run without Flask app context
- Async functions are hard to mock properly
- Error handling is mixed with business logic

## Refactoring Plan

### Phase 1: Identify and Extract Business Logic Functions
**Target**: `routes/game_data.py` - Pure data retrieval functions

1. **Extract Functions**:
   - `get_leaderboard_data()` - Pure function returning leaderboard list
   - `get_units_data()` - Pure function returning units list
   - `get_traits_data()` - Pure function returning traits list

2. **Modify Route Functions**:
   - `get_leaderboard()` → call `get_leaderboard_data()` + `jsonify()`
   - `get_units()` → call `get_units_data()` + `jsonify()`
   - `get_traits()` → call `get_traits_data()` + `jsonify()`

3. **Update Tests**:
   - Test pure functions directly (no Flask context needed)
   - Test routes separately with Flask test client

### Phase 2: Extract Game Management Logic
**Target**: `routes/game_management.py` - Game state operations

1. **Extract Functions**:
   - `get_player_state_data(user_id)` - Pure function returning player state dict
   - `create_new_game_data(user_id)` - Pure function for game creation
   - `reset_player_game_data(user_id)` - Pure function for game reset
   - `surrender_player_game_data(user_id, payload)` - Pure function for surrender

2. **Modify Route Functions**:
   - Keep auth decorators and HTTP response handling
   - Call pure business functions

3. **Update Tests**:
   - Test business logic without HTTP concerns
   - Test auth separately if needed

### Phase 3: Extract Game Actions Logic
**Target**: `routes/game_actions.py` - Player actions (buy, sell, move, etc.)

1. **Extract Functions**:
   - `buy_unit_action(user_id, unit_data)` - Pure buy logic
   - `sell_unit_action(user_id, unit_data)` - Pure sell logic
   - `move_unit_action(user_id, move_data)` - Pure move logic
   - `reroll_shop_action(user_id)` - Pure reroll logic
   - `toggle_lock_action(user_id)` - Pure lock toggle logic

2. **Modify Route Functions**:
   - Extract request data
   - Call pure functions
   - Return JSON responses

3. **Update Tests**:
   - Test actions with mock data structures
   - No Flask dependencies

### Phase 4: Extract Combat Logic
**Target**: `routes/game_combat.py` - Combat system

1. **Extract Functions**:
   - `start_combat_data(user_id)` - Pure combat logic
   - Returns combat results dict

2. **Modify Route Functions**:
   - Thin HTTP wrapper

3. **Update Tests**:
   - Test combat logic with mock players

### Phase 5: Update All Tests
**Target**: All test files

1. **Create Business Logic Test Files**:
   - `test_game_data_logic.py` - Test pure data functions
   - `test_game_management_logic.py` - Test game management
   - `test_game_actions_logic.py` - Test player actions
   - `test_game_combat_logic.py` - Test combat

2. **Keep HTTP Route Tests**:
   - `test_routes.py` - Test HTTP endpoints with Flask client
   - Focus on HTTP concerns (status codes, JSON format, auth)

## Implementation Order

### Stage 1: game_data.py (Easiest - no auth, pure data)
- ✅ Extract `get_leaderboard_data()`
- ⏳ Extract `get_units_data()`
- ⏳ Extract `get_traits_data()`
- ⏳ Update routes
- ⏳ Update tests

### Stage 2: game_management.py (Medium - auth required)
- ⏳ Extract state management functions
- ⏳ Update routes
- ⏳ Update tests

### Stage 3: game_actions.py (Complex - request parsing)
- ⏳ Extract action functions
- ⏳ Update routes
- ⏳ Update tests

### Stage 4: game_combat.py (Complex - combat simulation)
- ⏳ Extract combat functions
- ⏳ Update routes
- ⏳ Update tests

## Benefits
- **Testable**: Business logic can be tested without Flask
- **Maintainable**: Clear separation of concerns
- **Reusable**: Business functions can be used in different contexts
- **Debuggable**: Easier to isolate issues

## Success Criteria
- All business logic functions are pure (no Flask dependencies)
- Tests pass without Flask app context
- Route functions are thin HTTP wrappers
- Code coverage maintained or improved