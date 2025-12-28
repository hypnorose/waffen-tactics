#!/usr/bin/env python3
"""Debug seed 205 - find ALL events after seq=661"""
import sys
import random
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics/src')
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend')

from waffen_tactics.services.game_manager import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation

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

mrozu = next(u for u in player_units if u.name == 'Mrozu')

print("=== ALL events after seq=660 ===")
for et, ed in events:
    seq = ed.get('seq', -1)
    if seq > 660:
        print(f"seq={seq} type={et} ts={ed.get('timestamp'):.3f}")
        # Check if this affects Mrozu
        if et == 'state_snapshot':
            for pu in ed.get('player_units', []):
                if pu.get('id') == 'mrozu':
                    print(f"  → Snapshot: Mrozu HP={pu['hp']}")
                    break
        elif ed.get('unit_id') == 'mrozu' or ed.get('target_id') == 'mrozu':
            print(f"  → Affects Mrozu")
            if et == 'attack':
                print(f"     damage={ed.get('damage')} post_hp={ed.get('post_hp')} target_hp={ed.get('target_hp')}")
            elif et == 'effect_expired':
                print(f"     effect_type={ed.get('effect_type')} stat={ed.get('stat')}")

print(f"\nTotal events: {len(events)}")
print(f"Last event seq: {events[-1][1].get('seq')}")
print(f"Last event type: {events[-1][0]}")
