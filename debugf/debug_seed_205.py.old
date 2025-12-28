#!/usr/bin/env python3
"""Debug seed 205 HP desync"""
import sys
import random
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics/src')
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend')

from waffen_tactics.services.game_manager import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor

# Load game data
game_data = load_game_data()

# Prepare seed 205
seed = 205
random.seed(seed)

all_unit_ids = [u.id for u in game_data.units]
def get_unit(unit_id):
    return next(u for u in game_data.units if u.id == unit_id)

# Sample 20 unique unit ids and split into two teams (10/10)
sample_20 = random.sample(all_unit_ids, 20)
player_unit_ids = sample_20[:10]
opponent_unit_ids = sample_20[10:]

print(f"Seed {seed}")
print(f"Player units: {player_unit_ids}")
print(f"Opponent units: {opponent_unit_ids}")

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

# Run simulation
result = run_combat_simulation(player_units, opponent_units)

print(f"\nWinner: {result['winner']}")
print(f"Duration: {result['duration']:.2f}s")
print(f"Total events: {len(result['events'])}")

# Test event replay
events = result['events']
events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] == 'state_snapshot' else 1, x[1]['timestamp']))

# Find state_snapshots
state_snapshots = [event for event in events if event[0] == 'state_snapshot']
print(f"Total snapshots: {len(state_snapshots)}")

# Initialize reconstruction from first snapshot
reconstructor = CombatEventReconstructor()
first_snapshot = state_snapshots[0][1]
reconstructor.initialize_from_snapshot(first_snapshot)

# Process all events
for event_type, event_data in events:
    reconstructor.process_event(event_type, event_data)

# Get final reconstructed state
reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

# Compare final state - focus on Mrozu
print("\n=== Checking Mrozu (player unit) ===")
mrozu = next(u for u in player_units if u.name == 'Mrozu')
print(f"Simulation final HP: {mrozu.hp}")
print(f"Reconstructed HP: {reconstructed_player_units[mrozu.id]['hp']}")
print(f"Mismatch: {mrozu.hp} != {reconstructed_player_units[mrozu.id]['hp']}")

# Show all HP-related events for Mrozu
print("\n=== HP events for Mrozu ===")
mrozu_hp_events = []
for event_type, event_data in events:
    if event_type in ['attack', 'damage_over_time_tick', 'heal', 'state_snapshot']:
        # Check if this event involves Mrozu
        if event_data.get('unit_id') == mrozu.id or event_data.get('target_id') == mrozu.id:
            mrozu_hp_events.append((event_type, event_data))
        elif event_type == 'state_snapshot':
            # Check player units in snapshot
            for pu in event_data.get('player_units', []):
                if pu.get('id') == mrozu.id:
                    mrozu_hp_events.append((event_type, {'seq': event_data['seq'], 'timestamp': event_data['timestamp'], 'hp': pu['hp'], 'max_hp': pu['max_hp']}))
                    break

print(f"Found {len(mrozu_hp_events)} HP-related events for Mrozu")
for i, (etype, edata) in enumerate(mrozu_hp_events[-20:]):  # Last 20 events
    if etype == 'attack':
        print(f"{i}: {etype} seq={edata.get('seq')} ts={edata.get('timestamp'):.3f} damage={edata.get('applied_damage')} post_hp={edata.get('post_hp')} unit_hp={edata.get('unit_hp')} target_hp={edata.get('target_hp')}")
    elif etype == 'damage_over_time_tick':
        print(f"{i}: {etype} seq={edata.get('seq')} ts={edata.get('timestamp'):.3f} damage={edata.get('damage')} unit_hp={edata.get('unit_hp')}")
    elif etype == 'heal':
        print(f"{i}: {etype} seq={edata.get('seq')} ts={edata.get('timestamp'):.3f} amount={edata.get('amount')} new_hp={edata.get('new_hp')}")
    elif etype == 'state_snapshot':
        print(f"{i}: {etype} seq={edata.get('seq')} ts={edata.get('timestamp'):.3f} hp={edata.get('hp')}")
