#!/usr/bin/env python3
"""
Test for State Persistence Between Combat Rounds

This test runs the same teams through multiple combats to detect:
1. Effects persisting between rounds
2. Stats carrying over when they shouldn't
3. Any state mutation that survives between simulations
"""

import sys
import os
import json

# Add waffen-tactics to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.game_manager import GameManager
import random


def create_team(units_data, team_size, prefix, seed_offset=0):
    """Create a team of CombatUnits"""
    random.seed(42 + seed_offset)
    selected = random.sample(units_data, team_size)

    team = []
    for i, unit_data in enumerate(selected):
        team.append(CombatUnit(
            id=f"{prefix}_{i}",
            name=unit_data.name,
            hp=unit_data.stats.hp,
            attack=unit_data.stats.attack,
            defense=unit_data.stats.defense,
            attack_speed=unit_data.stats.attack_speed,
            position='front',
            max_mana=unit_data.stats.max_mana,
            skill=unit_data.skill,
            stats=unit_data.stats
        ))

    return team, selected


def snapshot_unit_state(unit):
    """Create a snapshot of unit's current state"""
    return {
        'id': unit.id,
        'name': unit.name,
        'hp': unit.hp,
        'max_hp': getattr(unit, 'max_hp', unit.hp),
        'attack': unit.attack,
        'defense': unit.defense,
        'attack_speed': unit.attack_speed,
        'current_mana': getattr(unit, 'current_mana', 0),
        'max_mana': unit.max_mana,
        'effects': list(getattr(unit, 'effects', [])),
        'shield': getattr(unit, 'shield', 0),
        '_stunned': getattr(unit, '_stunned', False),
        'stunned_expires_at': getattr(unit, 'stunned_expires_at', None),
    }


def compare_states(before, after, label):
    """Compare before/after states and report differences"""
    differences = []

    for key in before.keys():
        if key == 'effects':
            # Compare effects separately
            if len(before[key]) != len(after[key]):
                differences.append(f"  {key}: {len(before[key])} effects -> {len(after[key])} effects")
                differences.append(f"    Before: {before[key]}")
                differences.append(f"    After: {after[key]}")
            elif before[key] != after[key]:
                differences.append(f"  {key}: Effects changed")
                differences.append(f"    Before: {before[key]}")
                differences.append(f"    After: {after[key]}")
        elif before[key] != after[key]:
            differences.append(f"  {key}: {before[key]} -> {after[key]}")

    if differences:
        print(f"\n❌ {label} - State Changed:")
        for diff in differences:
            print(diff)
        return False
    else:
        print(f"✅ {label} - No state changes")
        return True


def test_persistence_between_combats():
    """Test if state persists between multiple combat simulations"""
    print("="*80)
    print("STATE PERSISTENCE TEST")
    print("="*80)
    print("\nTesting if unit state persists between combat rounds...")
    print()

    # Load game data
    game_manager = GameManager()
    units_data = game_manager.data.units

    # Create teams (use small teams for faster testing)
    team_size = 3
    print(f"Creating teams with {team_size} units each...")
    team_a, team_a_data = create_team(units_data, team_size, "player")
    team_b, team_b_data = create_team(units_data, team_size, "opp", seed_offset=100)

    print(f"Team A: {[u.name for u in team_a]}")
    print(f"Team B: {[u.name for u in team_b]}")
    print()

    # Snapshot initial state
    print("📸 Taking initial state snapshots...")
    initial_a = [snapshot_unit_state(u) for u in team_a]
    initial_b = [snapshot_unit_state(u) for u in team_b]

    print(f"Team A initial state:")
    for snapshot in initial_a:
        print(f"  {snapshot['name']}: hp={snapshot['hp']}, effects={len(snapshot['effects'])}, stunned={snapshot['_stunned']}")

    print(f"\nTeam B initial state:")
    for snapshot in initial_b:
        print(f"  {snapshot['name']}: hp={snapshot['hp']}, effects={len(snapshot['effects'])}, stunned={snapshot['_stunned']}")

    # Run multiple combats
    num_rounds = 3
    print(f"\n{'='*80}")
    print(f"Running {num_rounds} combat rounds with the SAME units...")
    print('='*80)

    all_passed = True

    for round_num in range(1, num_rounds + 1):
        print(f"\n{'─'*80}")
        print(f"ROUND {round_num}")
        print('─'*80)

        # Snapshot state BEFORE combat
        before_a = [snapshot_unit_state(u) for u in team_a]
        before_b = [snapshot_unit_state(u) for u in team_b]

        print(f"\nBefore combat {round_num}:")
        print(f"Team A: effects={[len(u['effects']) for u in before_a]}, stunned={[u['_stunned'] for u in before_a]}")
        print(f"Team B: effects={[len(u['effects']) for u in before_b]}, stunned={[u['_stunned'] for u in before_b]}")

        # Run combat
        events = []
        def callback(event_type, event_data):
            events.append((event_type, event_data))

        sim = CombatSimulator(dt=0.1, timeout=10)
        result = sim.simulate(team_a, team_b, event_callback=callback)

        winner = result.get('winner', 'unknown') if isinstance(result, dict) else getattr(result, 'winner', 'unknown')
        print(f"\nCombat {round_num} finished: {winner} won")
        print(f"Events captured: {len(events)}")

        # Check for early effects in events
        effect_events = [(t, d) for t, d in events if t in ['unit_stunned', 'stat_buff', 'damage_over_time_applied', 'shield_applied']]
        early_effects = [e for e in effect_events if e[1].get('seq', 999) <= 5]

        if early_effects:
            print(f"\n⚠️  Early effect events (seq <= 5): {len(early_effects)}")
            for event_type, event_data in early_effects[:5]:  # Show first 5
                print(f"  {event_type} at seq={event_data.get('seq')}, unit={event_data.get('unit_id')}")

        # Snapshot state AFTER combat
        after_a = [snapshot_unit_state(u) for u in team_a]
        after_b = [snapshot_unit_state(u) for u in team_b]

        print(f"\nAfter combat {round_num}:")
        print(f"Team A: effects={[len(u['effects']) for u in after_a]}, stunned={[u['_stunned'] for u in after_a]}")
        print(f"Team B: effects={[len(u['effects']) for u in after_b]}, stunned={[u['_stunned'] for u in after_b]}")

        # Compare with initial state
        print(f"\n📊 Comparing with INITIAL state (should be identical for next round):")

        for i, (unit, initial, after) in enumerate(zip(team_a, initial_a, after_a)):
            label = f"Round {round_num} - Team A Unit {i} ({unit.name})"
            passed = compare_states(initial, after, label)
            if not passed:
                all_passed = False

        for i, (unit, initial, after) in enumerate(zip(team_b, initial_b, after_b)):
            label = f"Round {round_num} - Team B Unit {i} ({unit.name})"
            passed = compare_states(initial, after, label)
            if not passed:
                all_passed = False

        # CRITICAL: Reset units to initial state for next round
        # This simulates what SHOULD happen between rounds
        print(f"\n🔄 Resetting units to initial state for next round...")

        for unit, initial in zip(team_a, initial_a):
            # Use canonical setter to restore HP
            try:
                unit._set_hp(initial['hp'], caller_module='event_canonicalizer')
            except Exception:
                unit.hp = initial['hp']
            unit.attack = initial['attack']
            unit.defense = initial['defense']
            unit.attack_speed = initial['attack_speed']
            unit.current_mana = 0
            unit.shield = 0
            unit.effects = []
            unit._stunned = False
            unit.stunned_expires_at = None

        for unit, initial in zip(team_b, initial_b):
            try:
                unit._set_hp(initial['hp'], caller_module='event_canonicalizer')
            except Exception:
                unit.hp = initial['hp']
            unit.attack = initial['attack']
            unit.defense = initial['defense']
            unit.attack_speed = initial['attack_speed']
            unit.current_mana = 0
            unit.shield = 0
            unit.effects = []
            unit._stunned = False
            unit.stunned_expires_at = None

    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print('='*80)

    if all_passed:
        print("✅ SUCCESS: All units returned to initial state after each combat")
        print("   No persistent state detected!")
        return 0
    else:
        print("❌ FAILURE: Some units have persistent state between combats")
        print("   This indicates state is NOT properly reset between rounds")
        print("\n   Likely causes:")
        print("   1. Effects list is mutated, not replaced")
        print("   2. Unit objects are reused without proper cleanup")
        print("   3. Stats are modified during combat and not reset")
        print("   4. Flags (_stunned, etc.) persist")
        return 1


def test_effects_cleared_on_init():
    """Test if manually clearing effects works"""
    print("\n" + "="*80)
    print("EFFECT CLEARING TEST")
    print("="*80)
    print("\nTesting if manually clearing effects prevents persistence...")
    print()

    game_manager = GameManager()
    units_data = game_manager.data.units

    team_a, _ = create_team(units_data, 2, "player")
    team_b, _ = create_team(units_data, 2, "opp", seed_offset=50)

    print(f"Team A: {[u.name for u in team_a]}")
    print(f"Team B: {[u.name for u in team_b]}")

    # Run first combat
    print("\n--- First Combat ---")
    events1 = []
    def callback1(t, d):
        events1.append((t, d))

    sim1 = CombatSimulator(dt=0.1, timeout=10)
    result1 = sim1.simulate(team_a, team_b, event_callback=callback1)

    print(f"After combat 1:")
    print(f"  Team A effects: {[len(u.effects) for u in team_a]}")
    print(f"  Team B effects: {[len(u.effects) for u in team_b]}")

    # Manually clear effects (as done in game_combat.py)
    print("\n🧹 Manually clearing effects...")
    for u in team_a + team_b:
        u.effects = []
        u._stunned = False
        u.stunned_expires_at = None

    print(f"After manual clear:")
    print(f"  Team A effects: {[len(u.effects) for u in team_a]}")
    print(f"  Team B effects: {[len(u.effects) for u in team_b]}")

    # Run second combat
    print("\n--- Second Combat ---")
    events2 = []
    def callback2(t, d):
        events2.append((t, d))

    sim2 = CombatSimulator(dt=0.1, timeout=10)
    result2 = sim2.simulate(team_a, team_b, event_callback=callback2)

    # Check first snapshot of second combat
    first_snapshot = next((d for t, d in events2 if t == 'state_snapshot'), None)

    if first_snapshot:
        player_effects = sum(len(u.get('effects', [])) for u in first_snapshot.get('player_units', []))
        opp_effects = sum(len(u.get('effects', [])) for u in first_snapshot.get('opponent_units', []))

        print(f"\nFirst snapshot of combat 2 (seq={first_snapshot.get('seq')}):")
        print(f"  Player effects in snapshot: {player_effects}")
        print(f"  Opponent effects in snapshot: {opp_effects}")

        if player_effects > 0 or opp_effects > 0:
            print("\n❌ PROBLEM FOUND: Effects present in first snapshot despite clearing!")
            print("   Effects are being added AFTER clear but BEFORE first snapshot")
            print("   AND no events are emitted for them")

            # Show what effects are there
            for u in first_snapshot.get('player_units', []):
                if u.get('effects'):
                    print(f"\n   Player {u['id']} ({u['name']}) has effects:")
                    for eff in u['effects']:
                        print(f"     - {eff.get('type')}: duration={eff.get('duration')}")

            for u in first_snapshot.get('opponent_units', []):
                if u.get('effects'):
                    print(f"\n   Opponent {u['id']} ({u['name']}) has effects:")
                    for eff in u['effects']:
                        print(f"     - {eff.get('type')}: duration={eff.get('duration')}")

            return 1
        else:
            print("\n✅ SUCCESS: No effects in first snapshot after clearing")
            return 0
    else:
        print("\n⚠️  No state_snapshot found in events")
        return 1


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("COMBAT STATE PERSISTENCE DEBUG TEST")
    print("█"*80)
    print("\nThis test checks if state persists between combat rounds")
    print("when using the same unit objects multiple times.\n")

    # Run both tests
    result1 = test_persistence_between_combats()
    result2 = test_effects_cleared_on_init()

    print("\n" + "█"*80)
    print("OVERALL RESULTS")
    print("█"*80)

    if result1 == 0 and result2 == 0:
        print("\n✅ ALL TESTS PASSED")
        print("   No persistent state issues detected")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED")
        print("   Persistent state issues found - see details above")
        sys.exit(1)
