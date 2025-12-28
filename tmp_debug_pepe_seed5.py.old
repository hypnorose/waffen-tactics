"""
Debug script for seed 5 focusing on unit 'pepe'
Dumps all events involving 'pepe' and replays through CombatEventReconstructor.
"""
import sys
sys.path.insert(0, 'waffen-tactics/src')
sys.path.insert(0, 'waffen-tactics-web/backend')

import random
random.seed(5)

from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.services.data_loader import load_game_data

# Load game data
from pprint import pprint

game_data = load_game_data()

# Select first 10 player units and next 10 opponent units
player_unit_ids = [u.id for u in game_data.units[:10]]
opponent_unit_ids = [u.id for u in game_data.units[10:20]]

def get_unit(unit_id):
    return next(u for u in game_data.units if u.id == unit_id)

# Build teams
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

print("="*80)
print("RUNNING SIMULATION WITH SEED 5 (pepe focus)")
print("="*80)

result = run_combat_simulation(player_units, opponent_units)

# Find pepe in player_units
pepe_sim = next((u for u in player_units if u.id == 'pepe'), None)
if pepe_sim is None:
    pepe_sim = next((u for u in opponent_units if u.id == 'pepe'), None)

print(f"\n✓ Simulation complete")
print(f"✓ Pepe final HP (simulation): {pepe_sim.hp if pepe_sim else 'N/A'}")

events = result.get('events', [])
# sort by seq then timestamp
events.sort(key=lambda x: (x[1].get('seq', 0), x[1].get('timestamp', 0)))

# Collect pepe-related events and state snapshots
pepe_events = []
for etype, edata in events:
    if etype in ('unit_attack', 'attack') and (edata.get('attacker_id') == 'pepe' or edata.get('target_id') == 'pepe'):
        pepe_events.append((etype, edata))
    elif etype == 'unit_heal' and edata.get('unit_id') == 'pepe':
        pepe_events.append((etype, edata))
    elif etype == 'unit_died' and edata.get('unit_id') == 'pepe':
        pepe_events.append((etype, edata))
    elif etype == 'state_snapshot':
        # check player units
        for u in edata.get('player_units', []):
            if u.get('id') == 'pepe':
                pepe_events.append((etype, {'seq': edata['seq'], 'timestamp': edata['timestamp'], 'hp': u.get('hp')}))
                break

print(f"\n✓ Found {len(pepe_events)} events related to Pepe")
print("\nPepe Event Timeline:\n" + "-"*60)
for i, (etype, edata) in enumerate(pepe_events, start=1):
    seq = edata.get('seq', 'N/A')
    ts = edata.get('timestamp', 'N/A')
    if etype in ('unit_attack', 'attack'):
        attacker = edata.get('attacker_name')
        target = edata.get('target_name')
        dmg = edata.get('damage')
        target_hp = edata.get('target_hp', '?')
        print(f"[{i}] seq={seq} ts={ts}: {etype} {attacker} -> {target}, dmg={dmg}, target_hp={target_hp}")
    elif etype == 'unit_heal':
        print(f"[{i}] seq={seq} ts={ts}: unit_heal {edata.get('healer_name')} -> {edata.get('unit_name')}, amount={edata.get('amount')}, new_hp={edata.get('new_hp')}")
    elif etype == 'unit_died':
        print(f"[{i}] seq={seq} ts={ts}: unit_died {edata.get('unit_name')}")
    elif etype == 'state_snapshot':
        print(f"[{i}] seq={seq} ts={ts}: state_snapshot hp={edata.get('hp')}")

print("\nREPLAYING EVENTS THROUGH CombatEventReconstructor")
reconstructor = CombatEventReconstructor()
# find first snapshot
first_snapshot = next((e[1] for e in events if e[0] == 'state_snapshot'), None)
if first_snapshot is None:
    print('No snapshot found in events; aborting')
    sys.exit(1)
reconstructor.initialize_from_snapshot(first_snapshot)

print('\nPepe HP changes during reconstruction:')
print('-'*60)
for etype, edata in events:
    old_hp = reconstructor.reconstructed_player_units.get('pepe', {}).get('hp') or reconstructor.reconstructed_opponent_units.get('pepe', {}).get('hp')
    reconstructor.process_event(etype, edata)
    new_hp = reconstructor.reconstructed_player_units.get('pepe', {}).get('hp') or reconstructor.reconstructed_opponent_units.get('pepe', {}).get('hp')
    if old_hp != new_hp:
        print(f"seq={edata.get('seq','N/A')}: {etype:15s} {old_hp} -> {new_hp}")

reconstructed_player, reconstructed_opponent = reconstructor.get_reconstructed_state()
pepe_recon_hp = (reconstructed_player.get('pepe') or reconstructed_opponent.get('pepe') or {}).get('hp')

print('\nFINAL COMPARISON:\n' + '='*60)
print(f"Pepe HP (simulation):     {pepe_sim.hp if pepe_sim else 'N/A'}")
print(f"Pepe HP (reconstructor):  {pepe_recon_hp}")
print(f"Difference:               { (pepe_recon_hp - pepe_sim.hp) if pepe_sim and pepe_recon_hp is not None else 'N/A'}")

if pepe_sim and pepe_recon_hp is not None and pepe_sim.hp != pepe_recon_hp:
    print('\nMISMATCH detected')
    # dump full event stream to file for further analysis
    with open('pepe_seed5_events.jsonl','w') as fh:
        import json
        for etype, edata in events:
            fh.write(json.dumps({'type': etype, 'data': edata}) + '\n')
    print('Wrote pepe_seed5_events.jsonl')
else:
    print('\nNo mismatch')
