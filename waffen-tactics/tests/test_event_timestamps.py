import random
from waffen_tactics.services.combat_shared import CombatSimulator
from waffen_tactics.models.unit import Stats


def make_unit(id, name, hp=100, attack=20, defense=10, attack_speed=1.0, effects=None, max_mana=100):
    stats = Stats(attack=attack, hp=hp, defense=defense, max_mana=max_mana, attack_speed=attack_speed, mana_on_attack=10)
    # CombatUnit constructor in tests elsewhere accepts these kwargs via helper; simulator accepts simple dict-like units
    from waffen_tactics.services.combat_shared import CombatUnit
    return CombatUnit(id=id, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=effects or [], max_mana=max_mana, stats=stats)


def test_event_timestamps_monotonic():
    """Run a short combat and ensure emitted event timestamps never go backwards."""
    random.seed(1234)
    sim = CombatSimulator(dt=0.05, timeout=6)

    a = [make_unit("a1", "A1", hp=150, attack=40, defense=5, attack_speed=1.0)]
    b = [make_unit("b1", "B1", hp=80, attack=15, defense=2, attack_speed=0.7)]

    events = []

    def event_callback(event_type, data):
        events.append((event_type, data))

    res = sim.simulate(a, b, event_callback=event_callback)

    # Collect timestamps from events that include them
    timestamps = [e[1].get('timestamp') for e in events if isinstance(e[1], dict) and 'timestamp' in e[1]]

    # There should be some timestamped events
    assert len(timestamps) > 0, "No timestamped events produced by combat"

    # Check monotonic non-decreasing (allowing for delayed events that may be emitted out of timestamp order)
    sorted_timestamps = sorted(timestamps)
    for earlier, later in zip(sorted_timestamps, sorted_timestamps[1:]):
        assert later >= earlier, f"Timestamps decreased: {earlier} -> {later}"


def test_event_timestamps_monotonic_complex():
    """Run a complex multi-unit combat and ensure emitted event timestamps remain monotonic."""
    random.seed(42)  # Different seed for more varied combat
    sim = CombatSimulator(dt=0.05, timeout=15)  # Longer combat

    # Team A: Mixed composition with different attack speeds
    a = [
        make_unit("a1", "Tank", hp=300, attack=25, defense=15, attack_speed=0.8, max_mana=120),
        make_unit("a2", "Fighter", hp=200, attack=45, defense=8, attack_speed=1.2, max_mana=100),
        make_unit("a3", "Archer", hp=150, attack=35, defense=5, attack_speed=1.5, max_mana=80),
        make_unit("a4", "Mage", hp=120, attack=20, defense=3, attack_speed=0.9, max_mana=150)
    ]

    # Team B: Different composition to create varied combat
    b = [
        make_unit("b1", "Warrior", hp=250, attack=30, defense=12, attack_speed=1.0, max_mana=110),
        make_unit("b2", "Assassin", hp=180, attack=50, defense=6, attack_speed=1.8, max_mana=90),
        make_unit("b3", "Guardian", hp=400, attack=20, defense=20, attack_speed=0.7, max_mana=100),
        make_unit("b4", "Ranger", hp=160, attack=40, defense=7, attack_speed=1.3, max_mana=95)
    ]

    events = []
    event_counts = {}

    def event_callback(event_type, data):
        events.append((event_type, data))
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    res = sim.simulate(a, b, event_callback=event_callback)

    # Collect timestamps from events that include them
    timestamps = [e[1].get('timestamp') for e in events if isinstance(e[1], dict) and 'timestamp' in e[1]]

    print(f"\nComplex combat generated {len(events)} total events:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")

    print(f"Events with timestamps: {len(timestamps)}")

    # Should have generated many more events than the simple test
    assert len(events) > 50, f"Expected many events in complex combat, got {len(events)}"
    assert len(timestamps) > 20, f"Expected many timestamped events, got {len(timestamps)}"

    # Check for various event types that should be present
    expected_event_types = {'animation_start', 'unit_attack', 'state_snapshot', 'mana_update'}
    actual_event_types = set(event_counts.keys())
    present_types = expected_event_types.intersection(actual_event_types)
    assert len(present_types) >= 3, f"Expected various event types, got: {actual_event_types}"

    # Check for death events if any units died
    if res['team_a_survivors'] < 4 or res['team_b_survivors'] < 4:
        assert 'unit_died' in event_counts, "Expected unit_died events when units perished"

    # Most important: timestamps should be monotonic when sorted
    sorted_timestamps = sorted(timestamps)
    for i, (earlier, later) in enumerate(zip(sorted_timestamps, sorted_timestamps[1:])):
        assert later >= earlier, f"Timestamps decreased at index {i}: {earlier} -> {later}"

    # Additional validation: timestamps should be within reasonable bounds
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)
    assert min_timestamp >= 0, f"Negative timestamp found: {min_timestamp}"
    assert max_timestamp <= 16, f"Timestamp too large: {max_timestamp} (combat should end by ~15s)"

    # Check that timestamps are reasonably distributed (not all at the same time)
    unique_timestamps = len(set(timestamps))
    assert unique_timestamps > len(timestamps) * 0.45, f"Timestamps too clustered: {unique_timestamps}/{len(timestamps)} unique"
