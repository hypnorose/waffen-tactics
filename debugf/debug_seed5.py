#!/usr/bin/env python3
"""Debug script to trace seed 5 HP reconstruction issue"""

import sys
import os
import random

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'waffen-tactics-web/backend'))

from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor

def debug_seed5():
    """Debug seed 5 HP reconstruction"""

    # Load game data
    game_data = load_game_data()

    # Get first 10 units for player team
    player_unit_ids = [u.id for u in game_data.units[:10]]
    opponent_unit_ids = [u.id for u in game_data.units[10:20]]

    # Helper to get unit by id
    def get_unit(unit_id):
        return next(u for u in game_data.units if u.id == unit_id)

    # Create player team (10 units)
    player_units = []
    for unit_id in player_unit_ids:
        unit = get_unit(unit_id)
        player_units.append(CombatUnit(
            id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
            defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
            position='front' if len(player_units) < 5 else 'back',
            stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
        ))

    # Create opponent team (10 units)
    opponent_units = []
    for unit_id in opponent_unit_ids:
        unit = get_unit(unit_id)
        opponent_units.append(CombatUnit(
            id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
            defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
            position='front' if len(opponent_units) < 5 else 'back',
            stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
        ))

    # Set seed 5
    seed = 5
    random.seed(seed)

    print(f"=== Testing seed {seed} ===\n")

    # Run simulation
    result = run_combat_simulation(player_units, opponent_units)

    # Get final HP from simulation
    print("Simulation Final HP:")
    for unit in player_units:
        print(f"  Player: {unit.name:20s} HP={unit.hp:4d}/{unit.max_hp}")
    for unit in opponent_units:
        print(f"  Opponent: {unit.name:20s} HP={unit.hp:4d}/{unit.max_hp}")

    print()

    # Test event replay
    events = result['events']
    events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] != 'state_snapshot' else 1, x[1]['timestamp']))

    # Find Mrvlook in the events
    print("Mrvlook-related events:")
    mrvlook_events = []
    for event_type, event_data in events:
        if event_data.get('target_name') == 'Mrvlook' or event_data.get('unit_name') == 'Mrvlook':
            mrvlook_events.append((event_type, event_data))

    for event_type, event_data in mrvlook_events:
        seq = event_data.get('seq', '?')
        if event_type in ['attack', 'unit_attack']:
            damage = event_data.get('damage', 0)
            target_hp = event_data.get('target_hp', '?')
            new_hp = event_data.get('new_hp', '?')
            print(f"  seq={seq:3d} {event_type:15s} damage={damage:3d} target_hp={target_hp} new_hp={new_hp}")
        elif event_type == 'unit_heal':
            heal = event_data.get('heal_amount', 0)
            new_hp = event_data.get('new_hp', '?')
            unit_hp = event_data.get('unit_hp', '?')
            print(f"  seq={seq:3d} {event_type:15s} heal={heal:3d} new_hp={new_hp} unit_hp={unit_hp}")
        elif event_type == 'state_snapshot':
            units = event_data.get('player_units', []) + event_data.get('opponent_units', [])
            for u in units:
                if u.get('name') == 'Mrvlook':
                    print(f"  seq={seq:3d} {event_type:15s} HP={u.get('hp', '?')}/{u.get('max_hp', '?')}")

    print()

    # Initialize reconstruction from first snapshot
    state_snapshots = [event for event in events if event[0] == 'state_snapshot']
    reconstructor = CombatEventReconstructor()
    first_snapshot = state_snapshots[0][1]
    reconstructor.initialize_from_snapshot(first_snapshot)

    print("Reconstruction process (Mrvlook only):")

    # Process all events with detailed logging for Mrvlook
    for event_type, event_data in events:
        # Check if this event affects Mrvlook
        affects_mrvlook = False
        mrvlook_id = None

        # Find Mrvlook's ID from the reconstruction state
        reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()
        for unit_id, unit_data in list(reconstructed_player_units.items()) + list(reconstructed_opponent_units.items()):
            if unit_data.get('name') == 'Mrvlook':
                mrvlook_id = unit_id
                break

        if mrvlook_id:
            if event_data.get('target_id') == mrvlook_id or event_data.get('unit_id') == mrvlook_id:
                affects_mrvlook = True

        # Get HP before processing
        hp_before = None
        if mrvlook_id:
            for unit_id, unit_data in list(reconstructed_player_units.items()) + list(reconstructed_opponent_units.items()):
                if unit_id == mrvlook_id:
                    hp_before = unit_data.get('hp')
                    break

        # Process the event
        reconstructor.process_event(event_type, event_data)

        # Get HP after processing
        if affects_mrvlook and mrvlook_id:
            reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()
            for unit_id, unit_data in list(reconstructed_player_units.items()) + list(reconstructed_opponent_units.items()):
                if unit_id == mrvlook_id:
                    hp_after = unit_data.get('hp')
                    seq = event_data.get('seq', '?')
                    delta = hp_after - hp_before if (hp_before is not None and hp_after is not None) else '?'

                    extra_info = ""
                    if event_type in ['attack', 'unit_attack']:
                        damage = event_data.get('damage', 0)
                        target_hp = event_data.get('target_hp', '?')
                        extra_info = f"damage={damage:3d} event_target_hp={target_hp}"

                    print(f"  seq={seq:3d} {event_type:15s} {hp_before:3d} -> {hp_after:3d} (Δ={delta}) {extra_info}")
                    break

    # Get final reconstructed state
    reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

    print("\nReconstruction Final HP:")
    for unit_id in [u.id for u in player_units]:
        if unit_id in reconstructed_player_units:
            unit_data = reconstructed_player_units[unit_id]
            print(f"  Player: {unit_data['name']:20s} HP={unit_data['hp']:4d}/{unit_data['max_hp']}")

    for unit_id in [u.id for u in opponent_units]:
        if unit_id in reconstructed_opponent_units:
            unit_data = reconstructed_opponent_units[unit_id]
            print(f"  Opponent: {unit_data['name']:20s} HP={unit_data['hp']:4d}/{unit_data['max_hp']}")

    print("\n=== Comparison ===")

    # Find Mrvlook in both
    mrvlook_sim = None
    for unit in opponent_units:
        if unit.name == 'Mrvlook':
            mrvlook_sim = unit
            break

    mrvlook_recon = None
    for unit_id, unit_data in reconstructed_opponent_units.items():
        if unit_data.get('name') == 'Mrvlook':
            mrvlook_recon = unit_data
            break

    if mrvlook_sim and mrvlook_recon:
        print(f"Mrvlook Simulation HP: {mrvlook_sim.hp}")
        print(f"Mrvlook Reconstruction HP: {mrvlook_recon['hp']}")
        print(f"Difference: {mrvlook_recon['hp'] - mrvlook_sim.hp}")

        if mrvlook_sim.hp != mrvlook_recon['hp']:
            print(f"\n❌ MISMATCH DETECTED: {mrvlook_sim.hp} != {mrvlook_recon['hp']}")
        else:
            print(f"\n✅ HP matches!")


if __name__ == '__main__':
    debug_seed5()
