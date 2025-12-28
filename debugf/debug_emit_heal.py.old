#!/usr/bin/env python3
"""Debug emit_unit_heal to see what it's actually emitting"""
import sys
import random
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics/src')
sys.path.insert(0, '/home/ubuntu/waffen-tactics-game/waffen-tactics-web/backend')

from waffen_tactics.services.game_manager import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation

# Monkey-patch event callback to see raw events
captured_events = []
def capture_callback(event_type, event_data):
    if event_type == 'unit_heal':
        print(f"[RAW EVENT] {event_type}: {event_data}")
    captured_events.append((event_type, event_data))

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

# Patch run_combat_simulation to use our callback
from waffen_tactics.services.combat_simulator import CombatSimulator

simulator = CombatSimulator()
result = simulator.simulate(
    team_a=player_units,
    team_b=opponent_units,
    event_callback=capture_callback
)

print("\n=== Looking for unit_heal events for Mrozu ===")
for et, ed in captured_events:
    if et == 'unit_heal' and ed.get('unit_id') == 'mrozu':
        print(f"Found: {ed}")
