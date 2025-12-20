"""
Deep debugging script for seed 5 HP mismatch
Traces every HP change for Mrvlook to find the 20 HP discrepancy
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
game_data = load_game_data()

# Get first 10 units for player team
player_unit_ids = [u.id for u in game_data.units[:10]]
opponent_unit_ids = [u.id for u in game_data.units[10:20]]

def get_unit(unit_id):
    return next(u for u in game_data.units if u.id == unit_id)

# Create player team
player_units = []
for unit_id in player_unit_ids:
    unit = get_unit(unit_id)
    player_units.append(CombatUnit(
        id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
        defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
        position='front' if len(player_units) < 5 else 'back',
        stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
    ))

# Create opponent team
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
print("RUNNING SIMULATION WITH SEED 5")
print("="*80)

# Run simulation
result = run_combat_simulation(player_units, opponent_units)

# Get Mrvlook's final HP from simulation
mrvlook_sim = next(u for u in opponent_units if u.id == 'mrvlook')
print(f"\n✓ Simulation complete")
print(f"✓ Mrvlook final HP (simulation): {mrvlook_sim.hp}")

print("\n" + "="*80)
print("ANALYZING EVENTS FOR MRVLOOK")
print("="*80)

events = result.get('events', [])
events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] != 'state_snapshot' else 1, x[1]['timestamp']))

# Find all events related to mrvlook
mrvlook_events = []
for event_type, event_data in events:
    if event_type in ['attack', 'unit_attack'] and event_data.get('target_id') == 'mrvlook':
        mrvlook_events.append((event_type, event_data))
    elif event_type == 'unit_died' and event_data.get('unit_id') == 'mrvlook':
        mrvlook_events.append((event_type, event_data))
    elif event_type == 'unit_heal' and event_data.get('unit_id') == 'mrvlook':
        mrvlook_events.append((event_type, event_data))
    elif event_type == 'state_snapshot':
        # Check if mrvlook is in the snapshot
        for u in event_data.get('opponent_units', []):
            if u['id'] == 'mrvlook':
                mrvlook_events.append((event_type, {'seq': event_data['seq'], 'hp': u['hp'], 'timestamp': event_data['timestamp']}))
                break

print(f"\n✓ Found {len(mrvlook_events)} events related to Mrvlook")

# Print all Mrvlook events
print("\nMrvlook Event Timeline:")
print("-" * 80)
for i, (event_type, event_data) in enumerate(mrvlook_events):
    seq = event_data.get('seq', 'N/A')
    ts = event_data.get('timestamp', 'N/A')

    if event_type in ['attack', 'unit_attack']:
        damage = event_data.get('damage', 0)
        target_hp = event_data.get('target_hp', '?')
        shield = event_data.get('shield_absorbed', 0)
        attacker = event_data.get('attacker_name', '?')
        print(f"  [{i+1}] seq={seq} ts={ts:.2f}: ATTACK by {attacker}, damage={damage}, shield_absorbed={shield}, target_hp={target_hp}")
    elif event_type == 'state_snapshot':
        hp = event_data.get('hp', '?')
        print(f"  [{i+1}] seq={seq} ts={ts:.2f}: SNAPSHOT hp={hp}")
    elif event_type == 'unit_died':
        print(f"  [{i+1}] seq={seq} ts={ts:.2f}: DIED")
    elif event_type == 'unit_heal':
        amount = event_data.get('amount', 0)
        new_hp = event_data.get('new_hp', '?')
        print(f"  [{i+1}] seq={seq} ts={ts:.2f}: HEAL amount={amount}, new_hp={new_hp}")

print("\n" + "="*80)
print("RECONSTRUCTING STATE FROM EVENTS")
print("="*80)

# Initialize reconstructor
reconstructor = CombatEventReconstructor()
first_snapshot = next(e[1] for e in events if e[0] == 'state_snapshot')
reconstructor.initialize_from_snapshot(first_snapshot)

print(f"✓ Initialized from first snapshot")

# Track Mrvlook HP through reconstruction
print("\nMrvlook HP changes during reconstruction:")
print("-" * 80)

for event_type, event_data in events:
    old_hp = reconstructor.reconstructed_opponent_units.get('mrvlook', {}).get('hp', '?')

    reconstructor.process_event(event_type, event_data)

    new_hp = reconstructor.reconstructed_opponent_units.get('mrvlook', {}).get('hp', '?')

    # Only print if HP changed
    if old_hp != new_hp:
        seq = event_data.get('seq', 'N/A')
        print(f"  seq={seq}: {event_type:20s} HP: {old_hp} -> {new_hp}")

# Get final reconstructed state
reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()
mrvlook_reconstructed_hp = reconstructed_opponent_units['mrvlook']['hp']

print("\n" + "="*80)
print("FINAL COMPARISON")
print("="*80)
print(f"\nMrvlook HP (simulation):     {mrvlook_sim.hp}")
print(f"Mrvlook HP (reconstruction): {mrvlook_reconstructed_hp}")
print(f"Difference:                  {mrvlook_reconstructed_hp - mrvlook_sim.hp}")

if mrvlook_sim.hp != mrvlook_reconstructed_hp:
    print(f"\n❌ MISMATCH DETECTED!")
    print(f"   Reconstruction is {mrvlook_reconstructed_hp - mrvlook_sim.hp} HP higher than simulation")
    print(f"   This suggests {abs(mrvlook_reconstructed_hp - mrvlook_sim.hp)} HP of damage is missing from events")
else:
    print(f"\n✅ HP values match!")
