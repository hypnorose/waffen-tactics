#!/usr/bin/env python3
"""
Example fight simulation to verify animation events in the event stream.

This script demonstrates the synchronized animation system where:
- animation_start events are emitted immediately when attacks occur
- damage/mana events are delayed by 0.2 seconds for smooth visual feedback
"""

import sys
import os
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'waffen-tactics', 'src'))

from waffen_tactics.services.combat_simulator import CombatSimulator


class MockUnit:
    """Mock unit for testing with minimal required attributes"""
    def __init__(self, id: str, name: str, attack: int = 20, defense: int = 10,
                 hp: int = 100, max_hp: int = 100, mana: int = 50, max_mana: int = 100,
                 attack_speed: float = 1.0):
        self.id = id
        self.name = name
        self.attack = attack
        self.defense = defense
        self.hp = hp
        self.max_hp = max_hp
        self.mana = mana
        self.max_mana = max_mana
        self.attack_speed = attack_speed
        self.stats = type('Stats', (), {'mana_on_attack': 10})()
        self.position = 'front'
        self.effects = []
        self.last_attack_time = 0

    def get_mana(self) -> int:
        return self.mana

    def to_dict(self, hp: int) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'hp': hp,
            'max_hp': self.max_hp,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'attack': self.attack,
            'defense': self.defense,
            'attack_speed': self.attack_speed
        }


def run_animation_test_simulation():
    """Run a simple combat simulation and analyze animation events"""

    print("🎮 Starting Animation Test Simulation")
    print("=" * 50)

    # Create test units
    warrior = MockUnit('warrior_1', 'Warrior', attack=25, defense=15, hp=120, attack_speed=1.2)
    goblin = MockUnit('goblin_1', 'Goblin', attack=15, defense=5, hp=80, attack_speed=0.8)

    print(f"⚔️  Warrior: {warrior.hp} HP, {warrior.attack} ATK, {warrior.attack_speed} SPD")
    print(f"👹 Goblin: {goblin.hp} HP, {goblin.attack} ATK, {goblin.attack_speed} SPD")
    print()

    # Track all events
    all_events: List[Dict[str, Any]] = []

    def event_callback(event_type: str, event: Dict[str, Any]) -> None:
        """Capture all events for analysis"""
        event_with_type = dict(event)
        event_with_type['event_type'] = event_type
        all_events.append(event_with_type)

        # Print animation events immediately
        if event_type == 'animation_start':
            print(f"🎬 [{event.get('timestamp', 0):.2f}s] ANIMATION: {event['animation_id']} "
                  f"({event['attacker_id']} → {event['target_id']})")

    # Create simulator
    simulator = CombatSimulator(dt=0.1, timeout=10.0)

    # Run simulation
    print("🏃 Running simulation...")
    result = simulator.simulate(
        team_a=[warrior],
        team_b=[goblin],
        event_callback=event_callback
    )

    print(f"\n🏆 Winner: {result['winner']}")
    print(f"⏱️  Duration: {result['duration']:.2f}s")
    print()

    # Analyze events
    analyze_animation_events(all_events)

    return result


def analyze_animation_events(events: List[Dict[str, Any]]) -> None:
    """Analyze the animation events in the event stream"""

    print("📊 Animation Event Analysis")
    print("=" * 30)

    # Extract animation events
    animation_events = [e for e in events if e['event_type'] == 'animation_start']
    damage_events = [e for e in events if e['event_type'] == 'unit_attack']
    mana_events = [e for e in events if e['event_type'] == 'mana_update']

    print(f"🎬 Animation events: {len(animation_events)}")
    print(f"⚔️  Damage events: {len(damage_events)}")
    print(f"🔵 Mana events: {len(mana_events)}")
    print()

    if not animation_events:
        print("❌ No animation events found! Animation system may not be working.")
        return

    # Analyze animation timing
    print("🎬 Animation Event Details:")
    for i, event in enumerate(animation_events[:5]):  # Show first 5
        ts = event.get('timestamp', 0)
        anim_id = event.get('animation_id', 'unknown')
        attacker = event.get('attacker_id', 'unknown')
        target = event.get('target_id', 'unknown')
        duration = event.get('duration', 0)

        print(f"  {i+1}. [{ts:.2f}s] {anim_id}: {attacker} → {target} ({duration}s)")

    if len(animation_events) > 5:
        print(f"  ... and {len(animation_events) - 5} more")
    print()

    # Check timing relationships
    print("⏰ Timing Analysis:")
    for i, anim_event in enumerate(animation_events[:3]):  # Check first 3 animations
        anim_ts = anim_event.get('timestamp', 0)
        anim_id = anim_event.get('animation_id', 'unknown')
        attacker = anim_event.get('attacker_id', 'unknown')

        # Find corresponding damage event
        damage_event = None
        for event in damage_events:
            if (event.get('attacker_id') == attacker and
                abs(event.get('timestamp', 0) - anim_ts - 0.2) < 0.01):  # Within 10ms
                damage_event = event
                break

        if damage_event:
            damage_ts = damage_event.get('timestamp', 0)
            delay = damage_ts - anim_ts
            print(f"  ✅ {anim_id}: Animation at {anim_ts:.2f}s, Damage at {damage_ts:.2f}s (delay: {delay:.2f}s)")
        else:
            print(f"  ❌ {anim_id}: No corresponding damage event found at expected time")

    print()

    # Check animation types
    animation_types = {}
    for event in animation_events:
        anim_type = event.get('animation_id', 'unknown')
        animation_types[anim_type] = animation_types.get(anim_type, 0) + 1

    print("📈 Animation Type Distribution:")
    for anim_type, count in animation_types.items():
        print(f"  {anim_type}: {count} events")
    print()

    # Verify synchronization
    print("🔍 Synchronization Check:")
    expected_delays = [e for e in events if e['event_type'] in ['unit_attack', 'mana_update']]
    sync_issues = 0

    for event in expected_delays:
        ts = event.get('timestamp', 0)
        event_type = event['event_type']

        # Check if there's a recent animation event (within 0.3s before)
        has_animation = any(
            anim_event['event_type'] == 'animation_start' and
            0 < (ts - anim_event.get('timestamp', 0)) < 0.3
            for anim_event in events
        )

        if not has_animation:
            print(f"  ⚠️  {event_type} at {ts:.2f}s has no preceding animation")
            sync_issues += 1

    if sync_issues == 0:
        print("  ✅ All damage/mana events have corresponding animations!")
    else:
        print(f"  ⚠️  Found {sync_issues} events without corresponding animations")

    print("\n🎉 Animation system verification complete!")


if __name__ == '__main__':
    try:
        result = run_animation_test_simulation()
        print(f"\nSimulation completed successfully. Winner: {result['winner']}")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()