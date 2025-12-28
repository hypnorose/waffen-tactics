#!/usr/bin/env python3
"""Debug OperatorKosiarki HP mismatch at seed 5"""

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

def debug_operatorkosiarki():
    """Debug OperatorKosiarki HP at seed 5"""

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

    print(f"=== Testing seed {seed} for OperatorKosiarki ===\n")

    # Run simulation
    result = run_combat_simulation(player_units, opponent_units)

    # Get final HP from simulation
    print("Simulation Final HP:")
    for unit in opponent_units:
        if unit.name == 'OperatorKosiarki':
            print(f"  OperatorKosiarki: HP={unit.hp}/{unit.max_hp}")

    print()

    # Test event replay
    events = result['events']
    events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] != 'state_snapshot' else 1, x[1]['timestamp']))

    # Find OperatorKosiarki events
    print("OperatorKosiarki-related events:")
    for event_type, event_data in events:
        if event_data.get('target_name') == 'OperatorKosiarki' or event_data.get('unit_name') == 'OperatorKosiarki':
            seq = event_data.get('seq', '?')
            if event_type in ['attack', 'unit_attack']:
                damage = event_data.get('damage', 0)
                target_hp = event_data.get('target_hp', '?')
                new_hp = event_data.get('new_hp', '?')
                is_skill = event_data.get('is_skill', False)
                skill_marker = " [SKILL]" if is_skill else ""
                print(f"  seq={seq:3d} {event_type:15s} damage={damage:3d} target_hp={target_hp} new_hp={new_hp}{skill_marker}")
            elif event_type == 'unit_heal':
                heal = event_data.get('heal_amount', 0)
                new_hp = event_data.get('new_hp', '?')
                unit_hp = event_data.get('unit_hp', '?')
                print(f"  seq={seq:3d} {event_type:15s} heal={heal:3d} new_hp={new_hp} unit_hp={unit_hp}")
            elif event_type == 'state_snapshot':
                units = event_data.get('player_units', []) + event_data.get('opponent_units', [])
                for u in units:
                    if u.get('name') == 'OperatorKosiarki':
                        print(f"  seq={seq:3d} {event_type:15s} HP={u.get('hp', '?')}/{u.get('max_hp', '?')}")
            elif event_type == 'unit_died':
                print(f"  seq={seq:3d} {event_type:15s}")

    print()

    # Initialize reconstruction from first snapshot
    state_snapshots = [event for event in events if event[0] == 'state_snapshot']
    reconstructor = CombatEventReconstructor()
    first_snapshot = state_snapshots[0][1]
    reconstructor.initialize_from_snapshot(first_snapshot)

    # Find OperatorKosiarki's ID
    operatorkosiarki_id = None
    for unit in opponent_units:
        if unit.name == 'OperatorKosiarki':
            operatorkosiarki_id = unit.id
            break

    print(f"OperatorKosiarki ID: {operatorkosiarki_id}")
    print()
    print("Reconstruction process (OperatorKosiarki only):")

    # Process all events with detailed logging
    for event_type, event_data in events:
        affects_unit = False
        if operatorkosiarki_id:
            if event_data.get('target_id') == operatorkosiarki_id or event_data.get('unit_id') == operatorkosiarki_id:
                affects_unit = True

        # Get HP before processing
        hp_before = None
        if operatorkosiarki_id and affects_unit:
            reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()
            if operatorkosiarki_id in reconstructed_opponent_units:
                hp_before = reconstructed_opponent_units[operatorkosiarki_id].get('hp')

        # Process the event
        reconstructor.process_event(event_type, event_data)

        # Get HP after processing
        if affects_unit and operatorkosiarki_id:
            reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()
            if operatorkosiarki_id in reconstructed_opponent_units:
                hp_after = reconstructed_opponent_units[operatorkosiarki_id].get('hp')
                seq = event_data.get('seq', '?')
                delta = hp_after - hp_before if (hp_before is not None and hp_after is not None) else '?'

                extra_info = ""
                if event_type in ['attack', 'unit_attack']:
                    damage = event_data.get('damage', 0)
                    target_hp = event_data.get('target_hp', '?')
                    is_skill = event_data.get('is_skill', False)
                    skill_marker = " [SKILL]" if is_skill else ""
                    extra_info = f"damage={damage:3d} event_target_hp={target_hp}{skill_marker}"

                print(f"  seq={seq:3d} {event_type:15s} {hp_before:3d} -> {hp_after:3d} (Δ={delta:4s}) {extra_info}")

    # Get final reconstructed state
    reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

    print("\n=== Comparison ===")

    # Find OperatorKosiarki in both
    operatorkosiarki_sim = None
    for unit in opponent_units:
        if unit.name == 'OperatorKosiarki':
            operatorkosiarki_sim = unit
            break

    operatorkosiarki_recon = None
    if operatorkosiarki_id and operatorkosiarki_id in reconstructed_opponent_units:
        operatorkosiarki_recon = reconstructed_opponent_units[operatorkosiarki_id]

    if operatorkosiarki_sim and operatorkosiarki_recon:
        print(f"OperatorKosiarki Simulation HP: {operatorkosiarki_sim.hp}")
        print(f"OperatorKosiarki Reconstruction HP: {operatorkosiarki_recon['hp']}")
        print(f"Difference: {operatorkosiarki_recon['hp'] - operatorkosiarki_sim.hp}")

        if operatorkosiarki_sim.hp != operatorkosiarki_recon['hp']:
            print(f"\n❌ MISMATCH DETECTED: {operatorkosiarki_sim.hp} != {operatorkosiarki_recon['hp']}")
        else:
            print(f"\n✅ HP matches!")


if __name__ == '__main__':
    debug_operatorkosiarki()
