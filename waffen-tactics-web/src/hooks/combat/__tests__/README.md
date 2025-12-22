# Combat Event Handler Tests

This directory contains comprehensive tests for the frontend combat event handling system using real combat event dumps from the backend.

## Test Files

### `applyEvent.test.ts`
Unit tests for the `applyCombatEvent` function covering:
- **Effect ID tracking** - Validates all effects have proper UUIDs
- **Effect type detection** - Ensures debuffs are correctly identified
- **Stat changes** - Verifies buffs/debuffs modify stats correctly
- **Effect expiration** - Tests stat reversion when effects expire
- **Immutability** - Validates deep copying prevents shared references
- **Shield and stun effects** - Tests all effect types

### `realEventReplay.test.ts`
Integration tests using actual backend combat dumps:
- **Full event replay** - Replays entire combats from JSON dumps
- **Desync detection** - Compares frontend state with backend snapshots
- **Effect ID validation** - Checks all effects have valid UUIDs
- **Duplicate detection** - Prevents same effect being added twice
- **Effect type validation** - Ensures debuffs match negative values

## Running Tests

### Install Dependencies
```bash
cd /home/ubuntu/waffen-tactics-game/waffen-tactics-web
npm install
```

### Run All Tests
```bash
npm test
```

### Run Tests in Watch Mode
```bash
npm test -- --watch
```

### Run with UI
```bash
npm run test:ui
```

### Run Specific Test File
```bash
npm test applyEvent.test.ts
```

### Run Tests Once (CI Mode)
```bash
npm run test:run
```

## Test Data

Tests use real combat event dumps from:
```
waffen-tactics-web/backend/events_*.json
```

These dumps contain complete combat replays with:
- All event types (attacks, buffs, shields, stuns, etc.)
- Backend state snapshots for validation
- Effect IDs and metadata
- Timestamps and sequence numbers

## What These Tests Catch

### ✅ Effect ID Bugs
**Before Fix:**
```javascript
// Backend sends effect_id, but frontend stores undefined
effect: { id: undefined, type: 'buff', ... }
```

**After Fix:**
```javascript
// Frontend correctly uses effect_id from event
effect: { id: 'uuid-123', type: 'buff', ... }
```

### ✅ Effect Type Bugs
**Before Fix:**
```javascript
// -25 defense debuff incorrectly labeled as buff
effect: { type: 'buff', value: -25 }  // WRONG!
```

**After Fix:**
```javascript
// Correctly detected as debuff by value sign
effect: { type: 'debuff', value: -25 }  // CORRECT!
```

### ✅ Effect Duplication
**Before Fix:**
```javascript
// Same effect added 3 times due to shallow copy bug
effects: [
  { id: 'same-uuid', type: 'buff' },
  { id: 'same-uuid', type: 'buff' },  // Duplicate!
  { id: 'same-uuid', type: 'buff' }   // Duplicate!
]
```

**After Fix:**
```javascript
// Each effect added only once
effects: [
  { id: 'uuid-1', type: 'buff' }  // Single instance
]
```

### ✅ State Desyncs
**Before Fix:**
```
UI:     attack=80, defense=15, effects=[buff, shield]
Server: attack=70, defense=25, effects=[debuff]
// Desyncs cause incorrect combat visualization
```

**After Fix:**
```
UI:     attack=70, defense=25, effects=[debuff]
Server: attack=70, defense=25, effects=[debuff]
// Perfect sync!
```

## Expected Test Results

After all fixes are applied, all tests should pass:

```
✓ applyCombatEvent - Effect Handling (15 tests)
  ✓ stat_buff events
    ✓ should add effect with proper ID from backend
    ✓ should detect debuff by negative value
    ✓ should apply stat changes correctly
    ✓ should store applied_delta for reversion
  ✓ effect_expired events
    ✓ should remove effect and revert stats
    ✓ should revert defense debuff correctly
  ✓ shield_applied events
    ✓ should add shield effect with ID
  ✓ unit_stunned events
    ✓ should add stun effect with ID
  ✓ Immutability
    ✓ should not mutate original state
    ✓ should not share effects array references
  ✓ Complex Effect Sequences
    ✓ should handle multiple buffs and debuffs correctly

✓ Real Combat Event Replay (8 tests)
  ✓ events_desync_team.json
    ✓ should replay all events without crashing
    ✓ should validate all stat_buff events have effect_id
    ✓ should validate effect types match value signs
    ✓ should detect desyncs (0 expected after fixes)
    ✓ should not create duplicate effects
  ✓ Multiple Dumps
    ✓ should replay events_test_1685.json without errors
    ✓ should replay events_test_3055.json without errors
    ✓ should replay events_seed42.json without errors

Test Files: 2 passed (2)
Tests:      23 passed (23)
Duration:   ~2s
```

## Debugging Failed Tests

### If "should detect desyncs" fails:
1. Check console output for desync details
2. Look at which stat/field is desyncing
3. Verify the event handler for that field is correct
4. Check if deep copying is working properly

### If "should not create duplicate effects" fails:
1. Check which effect ID is duplicated
2. Trace back to which event type added it
3. Verify effect handlers are using deep copy
4. Check if the same effect_id is being emitted multiple times by backend

### If "should validate effect types" fails:
1. Check which event has wrong type
2. Verify effect type detection logic (negative = debuff)
3. Check if backend is sending correct value signs

## Adding New Tests

To test a new combat scenario:

1. **Capture events from backend:**
   ```bash
   # Backend logs events to events_test_*.json automatically
   ```

2. **Add to test suite:**
   ```typescript
   it('should handle my-new-scenario', () => {
     const events = loadEventDump('events_my_scenario.json')
     // ... test logic
   })
   ```

3. **Run and verify:**
   ```bash
   npm test my-new-scenario
   ```

## CI Integration

Add to GitHub Actions workflow:
```yaml
- name: Run Frontend Tests
  run: |
    cd waffen-tactics-web
    npm ci
    npm run test:run
```

## Performance

Tests replay ~1000 events in ~2 seconds. If tests are slow:
- Use `test.skip()` to disable heavy tests during development
- Run specific test files instead of full suite
- Use `--reporter=dot` for less verbose output

## Future Improvements

- [ ] Add property-based testing (generate random events)
- [ ] Add visual regression tests for combat UI
- [ ] Add performance benchmarks (events/second)
- [ ] Add fuzzing to find edge cases
- [ ] Add snapshot testing for complex states
