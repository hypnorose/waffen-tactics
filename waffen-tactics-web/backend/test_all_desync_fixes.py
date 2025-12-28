#!/usr/bin/env python3
"""
Comprehensive test for all three desync fixes:
1. HP Desync (shield double-subtraction)
2. Defense Stat Desync (buffed_stats mutation)
3. Stun Event Missing (canonical emitter)

This test simulates a combat and validates that:
- All stun effects have corresponding unit_stunned events
- HP values are consistent throughout
- Defense stats remain correct when debuffs applied
"""
import sys
import os

# Add waffen-tactics to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../waffen-tactics/src'))

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.game_manager import GameManager
import random
import json


def print_banner(text):
    """Print a fancy banner"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def create_test_team(units_data, team_size, prefix, seed_offset=0):
    """Create a team with specific units for testing"""
    random.seed(42 + seed_offset)

    # Try to get units that have stun skills for testing
    units_with_skills = [u for u in units_data if u.skill]
    if len(units_with_skills) >= team_size:
        selected = random.sample(units_with_skills, team_size)
    else:
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
            stats=unit_data.stats,
            effects=[]  # CRITICAL: Start with empty effects
        ))

    return team


def test_stun_events():
    """Test Fix #3: Verify stun effects have corresponding events"""
    print_banner("TEST 1: Stun Events Emission")

    game_manager = GameManager()
    units_data = game_manager.data.units

    # Create teams
    team_a = create_test_team(units_data, 3, "player")
    team_b = create_test_team(units_data, 3, "opp", seed_offset=100)

    print("📋 Teams:")
    print(f"  Team A: {[u.name for u in team_a]}")
    print(f"  Team B: {[u.name for u in team_b]}")

    # Track all events
    events = []
    def event_callback(event_type, event_data):
        events.append((event_type, event_data))

    # Run combat
    print("\n🎮 Running combat simulation...")
    sim = CombatSimulator(dt=0.1, timeout=10)
    result = sim.simulate(team_a, team_b, event_callback=event_callback)

    print(f"✅ Combat finished: {result.get('winner', 'unknown')} won")
    print(f"📊 Total events captured: {len(events)}\n")

    # Find all state snapshots with stun effects
    snapshots_with_stuns = []
    for event_type, event_data in events:
        if event_type == 'state_snapshot':
            seq = event_data.get('seq', 0)
            game_state = event_data.get('game_state', {})

            all_units = game_state.get('player_units', []) + game_state.get('opponent_units', [])
            units_with_stuns = []

            for unit in all_units:
                stun_effects = [e for e in unit.get('effects', []) if e.get('type') == 'stun']
                if stun_effects:
                    units_with_stuns.append({
                        'unit_id': unit.get('id'),
                        'unit_name': unit.get('name'),
                        'stuns': stun_effects
                    })

            if units_with_stuns:
                snapshots_with_stuns.append({
                    'seq': seq,
                    'timestamp': event_data.get('timestamp', 0),
                    'units_with_stuns': units_with_stuns
                })

    # Find all unit_stunned events
    stun_events = []
    for event_type, event_data in events:
        if event_type == 'unit_stunned':
            stun_events.append({
                'seq': event_data.get('seq', 0),
                'timestamp': event_data.get('timestamp', 0),
                'unit_id': event_data.get('unit_id'),
                'unit_name': event_data.get('unit_name'),
                'duration': event_data.get('duration'),
                'effect_id': event_data.get('effect_id')
            })

    print(f"🎯 Found {len(stun_events)} unit_stunned events")
    if stun_events:
        for i, evt in enumerate(stun_events[:5], 1):  # Show first 5
            print(f"  {i}. seq={evt['seq']}, unit={evt['unit_name']}, duration={evt['duration']}s, effect_id={evt['effect_id'][:8]}...")
        if len(stun_events) > 5:
            print(f"  ... and {len(stun_events) - 5} more")

    print(f"\n🔍 Found {len(snapshots_with_stuns)} snapshots with stun effects")

    # VALIDATION: Every stun in snapshot must have a corresponding event
    test_passed = True
    for snapshot in snapshots_with_stuns:
        seq = snapshot['seq']
        print(f"\n  📸 Snapshot seq={seq} @ t={snapshot['timestamp']:.2f}s:")

        for unit_with_stun in snapshot['units_with_stuns']:
            unit_id = unit_with_stun['unit_id']
            unit_name = unit_with_stun['unit_name']
            stuns = unit_with_stun['stuns']

            print(f"    Unit {unit_name} ({unit_id}) has {len(stuns)} stun effect(s)")

            for stun_effect in stuns:
                effect_id = stun_effect.get('id')
                duration = stun_effect.get('duration')

                # Find corresponding event
                matching_events = [e for e in stun_events if e.get('effect_id') == effect_id]

                if matching_events:
                    evt = matching_events[0]
                    print(f"      ✅ Stun effect {effect_id[:8]}... HAS event at seq={evt['seq']}")
                else:
                    # Check if event exists for this unit (even without matching effect_id)
                    unit_events = [e for e in stun_events if e['unit_id'] == unit_id and e['seq'] <= seq]
                    if unit_events:
                        print(f"      ⚠️  Stun effect {effect_id[:8] if effect_id else 'NO-ID'}... has unit_stunned event but effect_id mismatch")
                    else:
                        print(f"      ❌ Stun effect {effect_id[:8] if effect_id else 'NO-ID'}... MISSING unit_stunned event!")
                        test_passed = False

    print("\n" + "-"*80)
    if test_passed:
        print("✅ TEST PASSED: All stun effects have corresponding events")
        return True
    else:
        print("❌ TEST FAILED: Some stun effects missing events")
        return False


def test_hp_consistency():
    """Test Fix #1: HP values remain consistent (no double shield subtraction)"""
    print_banner("TEST 2: HP Consistency")

    game_manager = GameManager()
    units_data = game_manager.data.units

    team_a = create_test_team(units_data, 2, "player")
    team_b = create_test_team(units_data, 2, "opp", seed_offset=50)

    print("📋 Teams:")
    print(f"  Team A: {[u.name for u in team_a]}")
    print(f"  Team B: {[u.name for u in team_b]}")

    events = []
    def event_callback(event_type, event_data):
        events.append((event_type, event_data))

    print("\n🎮 Running combat simulation...")
    sim = CombatSimulator(dt=0.1, timeout=10)
    result = sim.simulate(team_a, team_b, event_callback=event_callback)

    print(f"✅ Combat finished: {result.get('winner', 'unknown')} won")
    print(f"📊 Total events captured: {len(events)}\n")

    # Find attack events and compare with subsequent snapshots
    attack_events = [(t, d) for t, d in events if t == 'unit_attack']
    snapshots = [(t, d) for t, d in events if t == 'state_snapshot']

    print(f"🔍 Analyzing {len(attack_events)} attack events...\n")

    hp_mismatches = []
    for i, (event_type, attack_data) in enumerate(attack_events[:10], 1):  # Check first 10
        target_id = attack_data.get('target_id')
        damage = attack_data.get('damage', 0)
        shield_absorbed = attack_data.get('shield_absorbed', 0)

        # HP from attack event
        attack_event_hp = attack_data.get('target_hp') or attack_data.get('unit_hp') or attack_data.get('new_hp')

        if not attack_event_hp:
            continue

        # Find next snapshot after this attack
        attack_seq = attack_data.get('seq', 0)
        next_snapshot = None
        for snap_type, snap_data in snapshots:
            if snap_data.get('seq', 0) > attack_seq:
                next_snapshot = snap_data
                break

        if next_snapshot:
            game_state = next_snapshot.get('game_state', {})
            all_units = game_state.get('player_units', []) + game_state.get('opponent_units', [])

            target_unit = next((u for u in all_units if u.get('id') == target_id), None)
            if target_unit:
                snapshot_hp = target_unit.get('hp', 0)

                # Allow small tolerance due to regeneration
                if abs(snapshot_hp - attack_event_hp) > 5:
                    hp_mismatches.append({
                        'attack_seq': attack_seq,
                        'target': target_unit.get('name'),
                        'damage': damage,
                        'shield_absorbed': shield_absorbed,
                        'event_hp': attack_event_hp,
                        'snapshot_hp': snapshot_hp,
                        'diff': snapshot_hp - attack_event_hp
                    })
                else:
                    print(f"  {i}. ✅ Attack seq={attack_seq}: {target_unit.get('name')} HP {attack_event_hp} matches snapshot (±{abs(snapshot_hp - attack_event_hp)})")

    if hp_mismatches:
        print(f"\n⚠️  Found {len(hp_mismatches)} HP mismatches:")
        for mismatch in hp_mismatches:
            print(f"  ❌ seq={mismatch['attack_seq']}: {mismatch['target']} event HP={mismatch['event_hp']}, snapshot HP={mismatch['snapshot_hp']} (diff: {mismatch['diff']})")

    print("\n" + "-"*80)
    if not hp_mismatches:
        print("✅ TEST PASSED: HP values consistent between events and snapshots")
        return True
    else:
        print(f"❌ TEST FAILED: {len(hp_mismatches)} HP mismatches found")
        return False


def test_defense_buffed_stats():
    """Test Fix #2: buffed_stats.defense remains constant when debuffs applied"""
    print_banner("TEST 3: Defense buffed_stats Consistency")

    game_manager = GameManager()
    units_data = game_manager.data.units

    team_a = create_test_team(units_data, 2, "player")
    team_b = create_test_team(units_data, 2, "opp", seed_offset=75)

    print("📋 Teams:")
    print(f"  Team A: {[u.name for u in team_a]}")
    print(f"  Team B: {[u.name for u in team_b]}")

    events = []
    def event_callback(event_type, event_data):
        events.append((event_type, event_data))

    print("\n🎮 Running combat simulation...")
    sim = CombatSimulator(dt=0.1, timeout=10)
    result = sim.simulate(team_a, team_b, event_callback=event_callback)

    print(f"✅ Combat finished: {result.get('winner', 'unknown')} won")
    print(f"📊 Total events captured: {len(events)}\n")

    # Find defense debuff events
    defense_debuffs = []
    for event_type, event_data in events:
        if event_type == 'stat_buff':
            if event_data.get('stat') == 'defense' and (event_data.get('amount', 0) < 0 or event_data.get('buff_type') == 'debuff'):
                defense_debuffs.append(event_data)

    print(f"🔍 Found {len(defense_debuffs)} defense debuff events\n")

    # For each debuff, check snapshots before and after
    buffed_stats_changed = []
    for i, debuff in enumerate(defense_debuffs[:5], 1):  # Check first 5
        unit_id = debuff.get('unit_id')
        unit_name = debuff.get('unit_name')
        amount = debuff.get('amount', 0)
        debuff_seq = debuff.get('seq', 0)

        print(f"  {i}. Debuff seq={debuff_seq}: {unit_name} loses {abs(amount)} defense")

        # Find snapshot before and after
        snapshots = [(t, d) for t, d in events if t == 'state_snapshot']

        snapshot_before = None
        snapshot_after = None

        for snap_type, snap_data in snapshots:
            snap_seq = snap_data.get('seq', 0)
            if snap_seq < debuff_seq:
                snapshot_before = snap_data
            elif snap_seq >= debuff_seq and snapshot_after is None:
                snapshot_after = snap_data

        if snapshot_before and snapshot_after:
            game_state_before = snapshot_before.get('game_state', {})
            game_state_after = snapshot_after.get('game_state', {})

            all_units_before = game_state_before.get('player_units', []) + game_state_before.get('opponent_units', [])
            all_units_after = game_state_after.get('player_units', []) + game_state_after.get('opponent_units', [])

            unit_before = next((u for u in all_units_before if u.get('id') == unit_id), None)
            unit_after = next((u for u in all_units_after if u.get('id') == unit_id), None)

            if unit_before and unit_after:
                buffed_before = unit_before.get('buffed_stats', {}).get('defense', 0)
                buffed_after = unit_after.get('buffed_stats', {}).get('defense', 0)

                defense_before = unit_before.get('defense', 0)
                defense_after = unit_after.get('defense', 0)

                print(f"     Before: defense={defense_before}, buffed_stats.defense={buffed_before}")
                print(f"     After:  defense={defense_after}, buffed_stats.defense={buffed_after}")

                if buffed_before != buffed_after:
                    print(f"     ❌ buffed_stats.defense CHANGED from {buffed_before} to {buffed_after}!")
                    buffed_stats_changed.append({
                        'unit': unit_name,
                        'debuff_seq': debuff_seq,
                        'buffed_before': buffed_before,
                        'buffed_after': buffed_after
                    })
                else:
                    print(f"     ✅ buffed_stats.defense remained constant at {buffed_before}")

    print("\n" + "-"*80)
    if not buffed_stats_changed:
        print("✅ TEST PASSED: buffed_stats.defense remains constant when debuffs applied")
        return True
    else:
        print(f"❌ TEST FAILED: buffed_stats changed in {len(buffed_stats_changed)} cases")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("█"*80)
    print("  COMPREHENSIVE DESYNC FIX VALIDATION")
    print("█"*80)
    print("\nThis test validates all three desync fixes:")
    print("  1. HP Desync (shield double-subtraction)")
    print("  2. Defense Stat Desync (buffed_stats mutation)")
    print("  3. Stun Event Missing (canonical emitter)")

    results = {
        'stun_events': test_stun_events(),
        'hp_consistency': test_hp_consistency(),
        'defense_buffed_stats': test_defense_buffed_stats()
    }

    print("\n")
    print("█"*80)
    print("  FINAL RESULTS")
    print("█"*80)
    print()

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print()

    all_passed = all(results.values())

    if all_passed:
        print("🎉 ALL TESTS PASSED! All three desync fixes are working correctly.")
        return 0
    else:
        failed_tests = [name for name, passed in results.items() if not passed]
        print(f"⚠️  {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        print("   Please review the logs above for details.")
        return 1


if __name__ == '__main__':
    exit(main())
