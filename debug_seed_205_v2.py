#!/usr/bin/env python3
"""Debug seed 205 HP desync - show final snapshot"""
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

# Test event replay
events = result['events']
events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] == 'state_snapshot' else 1, x[1]['timestamp']))

# Find state_snapshots
state_snapshots = [event for event in events if event[0] == 'state_snapshot']

# Find Mrozu in final snapshot
mrozu = next(u for u in player_units if u.name == 'Mrozu')

print("=== Final 3 snapshots ===")
for snap_event in state_snapshots[-3:]:
    snap = snap_event[1]
    print(f"\nSnapshot seq={snap['seq']} ts={snap['timestamp']:.3f}")
    for pu in snap.get('player_units', []):
        if pu.get('id') == mrozu.id:
            print(f"  Mrozu HP: {pu['hp']} / {pu['max_hp']}")
            break

print(f"\n=== Simulation final state ===")
print(f"Mrozu HP: {mrozu.hp} / {mrozu.max_hp}")

print(f"\n=== Events after last snapshot ===")
last_snapshot = state_snapshots[-1][1]
last_snapshot_seq = last_snapshot['seq']
last_snapshot_ts = last_snapshot['timestamp']

print(f"Last snapshot: seq={last_snapshot_seq} ts={last_snapshot_ts:.3f}")
after_snapshot = [(et, ed) for et, ed in events if ed['seq'] > last_snapshot_seq]
print(f"Total events after last snapshot: {len(after_snapshot)}")

# Show Mrozu-related events after last snapshot
for et, ed in after_snapshot:
    if ed.get('unit_id') == mrozu.id or ed.get('target_id') == mrozu.id:
        if et == 'attack':
            print(f"  {et} seq={ed.get('seq')} ts={ed.get('timestamp'):.3f} damage={ed.get('applied_damage')} post_hp={ed.get('post_hp')}")
        elif et == 'damage_over_time_tick':
            print(f"  {et} seq={ed.get('seq')} ts={ed.get('timestamp'):.3f} damage={ed.get('damage')} unit_hp={ed.get('unit_hp')}")
