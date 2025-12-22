#!/usr/bin/env python3
"""
Generate test combat events with specific team compositions.

This script creates combats with teams designed to test edge cases:
- Multiple Srebrna Gwardia (shield effects)
- XN Waffen units (attack buffs)
- Hakerzy (stun effects)
- Mixed teams with various synergies
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))

from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_shared import CombatSimulator
import json


def create_test_team(team_name: str, unit_specs: list):
    """
    Create a team from unit specifications.

    Args:
        team_name: Name for the team (for logging)
        unit_specs: List of (unit_id, star_level, position) tuples

    Returns:
        List of CombatUnit objects
    """
    game_manager = GameManager()
    units = []

    for i, (unit_id, star_level, position) in enumerate(unit_specs):
        unit_data = next((u for u in game_manager.data.units if u.id == unit_id), None)
        if not unit_data:
            print(f"WARNING: Unit {unit_id} not found, skipping")
            continue

        from waffen_tactics.services.combat_unit import CombatUnit

        # Calculate stats with star scaling
        star_multiplier = star_level
        base_stats = unit_data.base_stats

        unit = CombatUnit(
            id=f"{team_name}_{i}",
            name=unit_data.name,
            hp=int(base_stats.hp * star_multiplier),
            attack=int(base_stats.attack * star_multiplier),
            defense=int(getattr(base_stats, 'defense', 0) * star_multiplier),
            attack_speed=getattr(base_stats, 'attack_speed', 1.0),
            star_level=star_level,
            position=position,
            max_mana=getattr(unit_data, 'max_mana', 100),
            skill=getattr(unit_data, 'skill', None),
            base_stats={
                'hp': base_stats.hp,
                'attack': base_stats.attack,
                'defense': getattr(base_stats, 'defense', 0),
                'attack_speed': getattr(base_stats, 'attack_speed', 1.0),
                'max_mana': getattr(unit_data, 'max_mana', 100)
            }
        )
        units.append(unit)

    return units


def run_test_combat(team_a_specs, team_b_specs, output_filename):
    """Run combat between two teams and save events to file."""

    print(f"\n{'='*60}")
    print(f"Running combat: {output_filename}")
    print(f"{'='*60}")

    # Create teams
    team_a = create_test_team('team_a', team_a_specs)
    team_b = create_test_team('team_b', team_b_specs)

    print(f"Team A: {[u.name for u in team_a]}")
    print(f"Team B: {[u.name for u in team_b]}")

    # Collect events
    all_events = []

    def event_collector(event_type: str, data: dict):
        event = {'type': event_type, **data}
        all_events.append(event)

    # Run combat
    simulator = CombatSimulator()
    result = simulator.simulate(team_a, team_b, event_collector)

    print(f"Winner: {result['winner']}")
    print(f"Duration: {result['duration']:.1f}s")
    print(f"Events collected: {len(all_events)}")

    # Count event types
    event_types = {}
    for event in all_events:
        event_type = event.get('type', 'unknown')
        event_types[event_type] = event_types.get(event_type, 0) + 1

    print(f"Event breakdown: {event_types}")

    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), output_filename)
    with open(output_path, 'w') as f:
        json.dump(all_events, f, indent=2)

    print(f"✓ Saved to {output_filename}")

    return all_events, result


if __name__ == '__main__':
    print("Generating test combat scenarios...")

    # Test 1: Multiple Srebrna Gwardia (shield effects)
    print("\n" + "="*60)
    print("TEST 1: Shield Effect Spam (Srebrna Gwardia)")
    print("="*60)

    srebrna_team = [
        ('srebrna_gwardia', 2, 'front'),
        ('srebrna_gwardia', 2, 'front'),
        ('srebrna_gwardia', 2, 'front'),
        ('srebrna_gwardia', 1, 'front'),
    ]

    basic_team = [
        ('xn_waffen', 1, 'front'),
        ('xn_waffen', 1, 'front'),
        ('dzidek', 1, 'front'),
    ]

    run_test_combat(srebrna_team, basic_team, 'test_shield_spam.json')

    # Test 2: XN Waffen stack (attack buffs)
    print("\n" + "="*60)
    print("TEST 2: Attack Buff Stack (XN Waffen)")
    print("="*60)

    xn_team = [
        ('xn_waffen', 2, 'front'),
        ('xn_waffen', 2, 'front'),
        ('xn_waffen', 1, 'front'),
        ('waffen_dzidek', 1, 'front'),
    ]

    run_test_combat(xn_team, basic_team, 'test_attack_buffs.json')

    # Test 3: Hakerzy (stun effects)
    print("\n" + "="*60)
    print("TEST 3: Stun Effect Spam (Hakerzy)")
    print("="*60)

    haker_team = [
        ('haker', 2, 'back'),
        ('haker', 2, 'back'),
        ('haker', 1, 'back'),
    ]

    tank_team = [
        ('dzidek', 2, 'front'),
        ('dzidek', 2, 'front'),
        ('dzidek', 1, 'front'),
    ]

    run_test_combat(haker_team, tank_team, 'test_stun_spam.json')

    # Test 4: Mixed synergies (complex effects)
    print("\n" + "="*60)
    print("TEST 4: Mixed Synergies (Various Effects)")
    print("="*60)

    mixed_team_a = [
        ('srebrna_gwardia', 2, 'front'),  # Shields
        ('haker', 2, 'back'),              # Stuns
        ('xn_waffen', 1, 'front'),         # Attack buffs
        ('woronicz', 1, 'back'),           # DoTs
    ]

    mixed_team_b = [
        ('dzidek', 2, 'front'),
        ('waffen_dzidek', 1, 'front'),
        ('atomowy_coggers', 1, 'front'),
        ('puszmen12', 1, 'back'),
    ]

    run_test_combat(mixed_team_a, mixed_team_b, 'test_mixed_effects.json')

    # Test 5: High star level units (big numbers)
    print("\n" + "="*60)
    print("TEST 5: High Star Levels (3-star units)")
    print("="*60)

    high_star_team = [
        ('xn_waffen', 3, 'front'),
        ('dzidek', 3, 'front'),
    ]

    run_test_combat(high_star_team, basic_team, 'test_high_stars.json')

    # Test 6: Defense buffs and debuffs
    print("\n" + "="*60)
    print("TEST 6: Defense Buff/Debuff Interactions")
    print("="*60)

    # Units with defense buffs
    defense_team = [
        ('srebrna_gwardia', 2, 'front'),
        ('dzidek', 2, 'front'),
        ('atomowy_coggers', 1, 'front'),
    ]

    # Units with armor reduction or damage
    damage_team = [
        ('xn_waffen', 2, 'front'),
        ('waffen_dzidek', 2, 'front'),
        ('woronicz', 1, 'back'),
    ]

    run_test_combat(defense_team, damage_team, 'test_defense_interactions.json')

    print("\n" + "="*60)
    print("✓ All test combats generated successfully!")
    print("="*60)
    print("\nGenerated files:")
    print("  - test_shield_spam.json")
    print("  - test_attack_buffs.json")
    print("  - test_stun_spam.json")
    print("  - test_mixed_effects.json")
    print("  - test_high_stars.json")
    print("  - test_defense_interactions.json")
    print("\nRun frontend tests with: npm test")
