# Comprehensive Combat Simulator vs UI Desync Testing Plan

## Executive Summary

Your project has two main desync types:
1. **HP Desyncs**: UI HP values diverge from server HP (UI often higher)
2. **Effect Desyncs**: Effects (stuns, buffs) present in server state but missing in UI

The testing plan focuses on systematic validation across multiple layers: backend emission, frontend reception, state reconstruction, and end-to-end scenarios.

## Phase 1: Backend Event Emission Validation

### 1.1 Canonical Emitter Compliance Test

**Objective**: Ensure all damage/effect sources use canonical emitters instead of direct state manipulation.

**Test Script**: Create `test_canonical_emitter_compliance.py`

```python
# Test all damage sources use emit_damage()
damage_sources = [
    'combat_attack_processor.py',
    'skill_executor.py',
    'effect_processor.py',
    'combat_per_second_buff_processor.py'
]

for file in damage_sources:
    # Check no direct HP manipulation
    assert not grep("defending_hp\[.*\] -= damage", file)
    assert not grep("target\.hp -= damage", file)
    # Check canonical emitter usage
    assert grep("emit_damage\(event_callback", file)
```

**Validation Commands**:
```bash
cd waffen-tactics-web/backend
python3 test_canonical_emitter_compliance.py
```

### 1.2 Event Completeness Test

**Objective**: Verify all events include required authoritative fields.

**Test Script**: `test_event_completeness.py`

```python
# For each event type, check required fields
required_fields = {
    'unit_attack': ['target_hp', 'damage', 'target_id', 'seq'],
    'unit_stunned': ['effect_id', 'unit_id', 'duration', 'seq'],
    'stat_buff': ['applied_delta', 'stat_type', 'recipient_id', 'seq'],
    'state_snapshot': ['player_units', 'opponent_units', 'seq']
}

# Run combat simulation and validate all events
```

## Phase 2: Frontend Event Processing Validation

### 2.1 Event Reception Test

**Objective**: Verify SSE events are received completely and in order.

**Browser Console Test**:
```javascript
// After combat, run in browser console
const events = eventLogger.getEvents();
console.log(`Total events received: ${events.length}`);

// Check for gaps in sequence
const sequences = events.map(e => e.event.seq).sort((a,b) => a-b);
const gaps = [];
for(let i = 1; i < sequences.length; i++) {
  if(sequences[i] !== sequences[i-1] + 1) {
    gaps.push(`${sequences[i-1]} → ${sequences[i]}`);
  }
}
console.log(`Sequence gaps: ${gaps.length > 0 ? gaps.join(', ') : 'None'}`);
```

### 2.2 Authoritative HP Usage Test

**Objective**: Ensure frontend never calculates HP locally, always uses backend values.

**Code Audit Script**: `audit_frontend_hp_usage.js`

```javascript
// Search for problematic patterns
const badPatterns = [
    /hp\s*-\s*damage/,  // Direct subtraction
    /oldHp\s*-\s*event\.damage/,  // Local calculation
    /Math\.max\(.*hp.*-\s*damage/,  // Complex local calc
];

filesToCheck.forEach(file => {
    badPatterns.forEach(pattern => {
        if(grep(pattern, file)) {
            console.error(`❌ Local HP calculation in ${file}`);
        }
    });
});
```

### 2.3 State Application Test

**Objective**: Verify events are applied correctly to UI state.

**Test Script**: `test_frontend_state_application.js`

```javascript
// Simulate event application
const testUnit = { hp: 100, effects: [] };
const testEvents = [
    { type: 'unit_attack', target_hp: 80, target_id: 'test' },
    { type: 'unit_stunned', effect_id: '123', unit_id: 'test', duration: 1.5 }
];

// Apply events and verify state
applyEvents(testUnit, testEvents);
assert(testUnit.hp === 80);
assert(testUnit.effects.length === 1);
```

## Phase 3: State Reconstruction Accuracy

### 3.1 Event Replay Validation

**Objective**: Verify that replaying events produces identical state to server snapshots.

**Enhanced Test Script**: `test_state_reconstruction.py`

```python
def test_state_reconstruction():
    # Run combat simulation
    events, snapshots = run_combat_simulation(seed=42)

    # Reconstruct state from events
    reconstructor = CombatEventReconstructor()
    reconstructed_state = reconstructor.replay_events(events)

    # Compare with snapshots at each sequence
    for seq, snapshot in snapshots.items():
        reconstructed = reconstructed_state.get_state_at_seq(seq)
        assert_states_equal(reconstructed, snapshot, seq)

def assert_states_equal(reconstructed, snapshot, seq):
    for unit_id in snapshot['units']:
        r_unit = reconstructed['units'][unit_id]
        s_unit = snapshot['units'][unit_id]

        # HP comparison
        if r_unit['hp'] != s_unit['hp']:
            raise AssertionError(f"HP desync at seq {seq}, unit {unit_id}: {r_unit['hp']} != {s_unit['hp']}")

        # Effects comparison
        r_effects = sorted([e['type'] for e in r_unit['effects']])
        s_effects = sorted([e['type'] for e in s_unit['effects']])
        if r_effects != s_effects:
            raise AssertionError(f"Effect desync at seq {seq}, unit {unit_id}: {r_effects} != {s_effects}")
```

### 3.2 Snapshot Synchronization Test

**Objective**: Verify `overwriteSnapshots` functionality works correctly.

**Browser Test**:
```javascript
// Test snapshot overwriting
localStorage.setItem('combat.overwriteSnapshots', 'true');

// Run combat and check console logs
// Should see: "[SNAPSHOT] Overwriting UI state with server snapshot"

// Verify UI state matches server after snapshots
setTimeout(() => {
    const uiState = getCurrentUIState();
    const serverState = getLastServerSnapshot();
    compareStates(uiState, serverState);
}, 2000);
```

## Phase 4: End-to-End Combat Scenarios

### 4.1 Comprehensive Scenario Testing

**Objective**: Test various combat situations that commonly cause desyncs.

**Test Scenarios**:
```python
test_scenarios = [
    {
        'name': 'Basic Attack Chain',
        'units': ['Szałwia', 'Yossarian', 'FalconBalkon'],
        'opponents': ['Stalin', 'Buba', 'Beudzik'],
        'expected_events': ['unit_attack', 'state_snapshot'],
        'validate': lambda: check_hp_consistency()
    },
    {
        'name': 'Stun-Heavy Combat',
        'units': ['Miki', 'RafcikD'],  # Miki has stun skills
        'opponents': ['Puszmen12', 'Wu_hao'],
        'expected_events': ['unit_stunned', 'skill_cast', 'state_snapshot'],
        'validate': lambda: check_stun_events_present()
    },
    {
        'name': 'Buff/Debuff Chain',
        'units': ['High Defense Unit', 'Buff Caster'],
        'opponents': ['Debuff Target', 'Stat Modifier'],
        'expected_events': ['stat_buff', 'effect_expired'],
        'validate': lambda: check_buffed_stats_consistency()
    },
    {
        'name': 'Regeneration Combat',
        'units': ['Regen Unit', 'Healer'],
        'opponents': ['Damage Dealer', 'DoT Caster'],
        'expected_events': ['heal', 'damage_over_time_applied'],
        'validate': lambda: check_regen_vs_damage_balance()
    }
]
```

### 4.2 Edge Case Testing

**Objective**: Test boundary conditions and error scenarios.

**Edge Cases**:
- Combat with 1 HP remaining units
- Effects expiring at exact combat end
- Multiple overlapping effects on same unit
- Units with extreme stat values (0 defense, 1000 HP)
- Network interruption during SSE stream
- Browser refresh during combat

### 4.3 Performance and Load Testing

**Objective**: Ensure desync detection doesn't impact performance.

**Performance Test**:
```python
def test_performance_impact():
    # Measure combat simulation time with/without desync validation
    start = time.time()
    run_combat_with_validation(seed=42, validate_desyncs=True)
    with_validation = time.time() - start

    start = time.time()
    run_combat_with_validation(seed=42, validate_desyncs=False)
    without_validation = time.time() - start

    # Should be < 10% performance impact
    assert with_validation < without_validation * 1.1
```

## Phase 5: Automated Regression Testing

### 5.1 CI/CD Integration

**Objective**: Prevent future desyncs with automated testing.

**GitHub Actions Workflow**:
```yaml
name: Desync Regression Tests
on: [push, pull_request]

jobs:
  test-desyncs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd waffen-tactics
          pip install -r requirements.txt
      - name: Run desync tests
        run: |
          cd waffen-tactics-web/backend
          python3 test_all_desync_fixes.py
          python3 test_state_reconstruction.py --seeds 1-100
      - name: Frontend tests
        run: |
          cd waffen-tactics-web
          npm install
          npm run test:desync
```

### 5.2 Daily Health Checks

**Objective**: Monitor for desyncs in production.

**Monitoring Script**: `daily_desync_health_check.py`

```python
def daily_health_check():
    # Run sample combats daily
    seeds_to_test = [5, 42, 205]  # Known problematic seeds

    for seed in seeds_to_test:
        events, snapshots = run_combat_simulation(seed)
        reconstructed = replay_events(events)

        if not states_match(reconstructed, snapshots):
            alert_team(f"Desync detected in daily health check, seed {seed}")
            save_debug_data(seed, events, snapshots, reconstructed)
```

## Phase 6: Debugging and Monitoring Tools

### 6.1 Enhanced Logging

**Objective**: Improve debugging capabilities.

**Backend Logging Enhancement**:
```python
# Add to combat_simulator.py
def log_event_emission(event_type, payload, seq):
    logger.info(f"[EVENT_EMITTED] {event_type} seq={seq}: {json.dumps(payload, indent=2)}")

# Add to event_canonicalizer.py
def emit_damage(event_callback, **kwargs):
    payload = build_damage_payload(**kwargs)
    logger.info(f"[EMIT_DAMAGE] {payload['target_id']} HP: {payload.get('target_hp', 'MISSING')}")
    if event_callback:
        event_callback('unit_attack', payload)
```

### 6.2 Real-time Desync Detection

**Objective**: Catch desyncs during development.

**Browser Extension**: `desync-detector.js`

```javascript
// Inject into combat page
window.desyncDetector = {
    lastServerSnapshot: null,
    checkInterval: setInterval(() => {
        const uiState = extractUIState();
        const serverState = this.lastServerSnapshot;

        if(serverState && !statesEqual(uiState, serverState)) {
            console.error('🚨 REAL-TIME DESYNC DETECTED:',
                compareStates(uiState, serverState));
        }
    }, 1000)
};
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Create test framework scripts
- [ ] Implement Phase 1 backend validation
- [ ] Set up automated test runner

### Week 2: Frontend Validation
- [ ] Complete Phase 2 frontend tests
- [ ] Implement Phase 3 reconstruction validation
- [ ] Fix any issues found

### Week 3: Scenario Testing
- [ ] Run Phase 4 comprehensive scenarios
- [ ] Test edge cases and performance
- [ ] Document all test cases

### Week 4: Automation & Monitoring
- [ ] Implement Phase 5 CI/CD integration
- [ ] Set up daily health checks
- [ ] Create Phase 6 debugging tools

## Success Metrics

- **0 desyncs** in all test scenarios
- **< 5% performance impact** from validation code
- **100% event emission compliance** with canonical emitters
- **Complete state reconstruction** accuracy
- **Automated detection** of future desyncs

## Risk Mitigation

- **Fallback mechanisms**: If desync detected, force UI refresh with server state
- **Graceful degradation**: Disable non-critical features if desyncs occur
- **User feedback**: Clear indicators when desyncs are detected
- **Rollback plan**: Ability to revert to last known good state

This plan provides systematic coverage of all desync sources while establishing long-term prevention mechanisms. The phased approach allows for iterative improvement and validation at each step.</content>
<parameter name="filePath">/home/ubuntu/waffen-tactics-game/COMPREHENSIVE_DESYNC_TESTING_PLAN.md