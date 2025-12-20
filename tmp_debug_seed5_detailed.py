"""
Detailed debugging for seed 5 HP mismatch
Focus on understanding HP changes and potential missing events
"""
import sys
sys.path.insert(0, 'waffen-tactics/src')
sys.path.insert(0, 'waffen-tactics-web/backend')

import random
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.data_loader import load_game_data

game_data = load_game_data()
player_unit_ids = [u.id for u in game_data.units[:10]]
opponent_unit_ids = [u.id for u in game_data.units[10:20]]

def get_unit(unit_id):
    return next(u for u in game_data.units if u.id == unit_id)

# Create teams ONCE
player_units = []
for unit_id in player_unit_ids:
    unit = get_unit(unit_id)
    player_units.append(CombatUnit(
        id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
        defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
        position='front' if len(player_units) < 5 else 'back',
        stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
    ))

opponent_units = []
for unit_id in opponent_unit_ids:
    unit = get_unit(unit_id)
    opponent_units.append(CombatUnit(
        id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
        defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
        position='front' if len(opponent_units) < 5 else 'back',
        stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
    ))

# Run seeds 4 and 5
for seed in [4, 5]:
    print(f"\n{'='*80}")
    print(f"SEED {seed}")
    print(f"{'='*80}")

    mrvlook = next(u for u in opponent_units if u.id == 'mrvlook')
    print(f"Mrvlook HP before simulation: {mrvlook.hp}")

    random.seed(seed)
    result = run_combat_simulation(player_units, opponent_units)

    print(f"Mrvlook HP after simulation:  {mrvlook.hp}")

    # Reconstruct
    events = result.get('events', [])
    events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] != 'state_snapshot' else 1, x[1]['timestamp']))

    # Count Mrvlook-related events
    mrvlook_attacks = [e for e in events if e[0] in ['attack', 'unit_attack'] and e[1].get('target_id') == 'mrvlook']
    print(f"Attack events targeting Mrvlook: {len(mrvlook_attacks)}")

    # Show first snapshot HP
    first_snapshot = next(e[1] for e in events if e[0] == 'state_snapshot')
    mrvlook_snapshot = next(u for u in first_snapshot['opponent_units'] if u['id'] == 'mrvlook')
    print(f"Mrvlook HP in first snapshot:  {mrvlook_snapshot['hp']}")

    # Reconstruct
    reconstructor = CombatEventReconstructor()
    reconstructor.initialize_from_snapshot(first_snapshot)

    # Track every HP change for Mrvlook
    hp_changes = []
    for event_type, event_data in events:
        old_hp = reconstructor.reconstructed_opponent_units.get('mrvlook', {}).get('hp', None)
        reconstructor.process_event(event_type, event_data)
        new_hp = reconstructor.reconstructed_opponent_units.get('mrvlook', {}).get('hp', None)

        if old_hp != new_hp and old_hp is not None:
            seq = event_data.get('seq', '?')
            damage = event_data.get('damage', 0)
            target_hp = event_data.get('target_hp', '?')
            hp_changes.append((seq, event_type, old_hp, new_hp, damage, target_hp))

    print(f"\nMrvlook HP changes in reconstruction ({len(hp_changes)} changes):")
    for seq, etype, old_hp, new_hp, damage, target_hp in hp_changes:
        delta = new_hp - old_hp
        print(f"  seq={seq:3d} {etype:20s} {old_hp:3d} -> {new_hp:3d} (delta={delta:4d}, dmg={damage}, event_target_hp={target_hp})")

    _, reconstructed_opponent_units = reconstructor.get_reconstructed_state()
    mrvlook_recon = reconstructed_opponent_units['mrvlook']['hp']

    print(f"\nFinal: sim={mrvlook.hp} recon={mrvlook_recon} diff={mrvlook_recon - mrvlook.hp}")

print(f"\n{'='*80}")
print("ANALYSIS")
print(f"{'='*80}")
print("The 20 HP difference at seed 5 suggests:")
print("1. An attack event is missing from the event stream, OR")
print("2. An attack event has wrong target_hp value, OR")
print("3. The reconstructor is not processing an event correctly")
