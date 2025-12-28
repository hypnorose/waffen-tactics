#!/usr/bin/env python3
"""Debug seed 205 HP desync - trace reconstructor processing"""
import sys
import random
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics/src')
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend')

from waffen_tactics.services.game_manager import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor

# Patch reconstructor to log Mrozu HP changes
original_process_damage = CombatEventReconstructor._process_damage_event
def patched_process_damage(self, event_data):
    target_id = event_data.get('target_id')
    if target_id == 'mrozu':
        unit_dict = self._get_unit_dict(target_id)
        old_hp = unit_dict['hp'] if unit_dict else None
        print(f"[RECON] Before damage event seq={event_data.get('seq')}: Mrozu HP={old_hp}")
        print(f"[RECON]   Event fields: damage={event_data.get('damage')}, target_hp={event_data.get('target_hp')}, new_hp={event_data.get('new_hp')}, post_hp={event_data.get('post_hp')}, unit_hp={event_data.get('unit_hp')}")
    result = original_process_damage(self, event_data)
    if target_id == 'mrozu':
        unit_dict = self._get_unit_dict(target_id)
        new_hp = unit_dict['hp'] if unit_dict else None
        print(f"[RECON] After damage event seq={event_data.get('seq')}: Mrozu HP={new_hp}")
    return result

CombatEventReconstructor._process_damage_event = patched_process_damage

# Patch snapshot processing
original_process_snapshot = CombatEventReconstructor._process_state_snapshot_event
def patched_process_snapshot(self, event_data):
    seq = event_data.get('seq')
    if seq >= 650:  # Only log near the end
        unit_dict = self.reconstructed_player_units.get('mrozu')
        before_hp = unit_dict['hp'] if unit_dict else None
        print(f"[RECON] Before snapshot seq={seq}: Mrozu HP={before_hp}")
        # Find Mrozu in snapshot
        for pu in event_data.get('player_units', []):
            if pu.get('id') == 'mrozu':
                print(f"[RECON]   Snapshot says Mrozu HP={pu['hp']}")
                break
    result = original_process_snapshot(self, event_data)
    if seq >= 650:
        unit_dict = self.reconstructed_player_units.get('mrozu')
        after_hp = unit_dict['hp'] if unit_dict else None
        print(f"[RECON] After snapshot seq={seq}: Mrozu HP={after_hp}")
    return result

CombatEventReconstructor._process_state_snapshot_event = patched_process_snapshot

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
print("Running simulation...")
result = run_combat_simulation(player_units, opponent_units)

# Test event replay
events = result['events']
events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] == 'state_snapshot' else 1, x[1]['timestamp']))

# Find state_snapshots
state_snapshots = [event for event in events if event[0] == 'state_snapshot']

# Initialize reconstruction from first snapshot
print("\nInitializing reconstructor from first snapshot...")
reconstructor = CombatEventReconstructor()
first_snapshot = state_snapshots[0][1]
reconstructor.initialize_from_snapshot(first_snapshot)

# Process events from seq=650 onwards
print("\nProcessing events from seq=650 onwards...")
for event_type, event_data in events:
    seq = event_data.get('seq', -1)
    if seq >= 650:
        reconstructor.process_event(event_type, event_data)
    elif seq < 650:
        # Process silently
        reconstructor.process_event(event_type, event_data)

# Get final reconstructed state
reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

mrozu = next(u for u in player_units if u.name == 'Mrozu')
print(f"\n=== FINAL COMPARISON ===")
print(f"Simulation final HP: {mrozu.hp}")
print(f"Reconstructed HP: {reconstructed_player_units[mrozu.id]['hp']}")
print(f"Difference: {reconstructed_player_units[mrozu.id]['hp'] - mrozu.hp}")
