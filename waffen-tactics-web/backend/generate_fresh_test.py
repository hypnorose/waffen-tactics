#!/usr/bin/env python3
"""Generate fresh combat event dump to test shield effect_id fix."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))

from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.services.combat_shared import CombatSimulator as SharedCombatSimulator, CombatUnit
from waffen_tactics.services.combat_simulator import CombatSimulator
import json

# Initialize game manager
gm = GameManager()

# Create test teams
player_units = [CombatUnit(
    id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack,
    defense=u.stats.defense, attack_speed=u.stats.attack_speed,
    position='front', stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana
) for u in gm.data.units[:4]]
opponent_units = [CombatUnit(
    id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack,
    defense=u.stats.defense, attack_speed=u.stats.attack_speed,
    position='front', stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana
) for u in gm.data.units[4:8]]

# Run combat and collect events
all_events = []

def event_collector(event_type: str, data: dict):
    event = {'type': event_type, **data}
    all_events.append(event)

# Run simulation
simulator = CombatSimulator()
result = simulator.simulate(player_units, opponent_units, event_collector)

print(f'Combat finished. Winner: {result["winner"]}, Events: {len(all_events)}')

# Count shield_applied events
shield_events = [e for e in all_events if e.get('type') == 'shield_applied']
print(f'Shield events: {len(shield_events)}')

# Check if they have effect_id
missing_ids = [e for e in shield_events if not e.get('effect_id')]
print(f'Shield events missing effect_id: {len(missing_ids)}')

if missing_ids:
    print('WARNING: Shield events still missing effect_id!')
    print('First missing:', missing_ids[0])
else:
    print('✓ All shield events have effect_id!')

# Save to new file
output_file = os.path.join(os.path.dirname(__file__), 'events_test_fresh.json')
with open(output_file, 'w') as f:
    json.dump(all_events, f, indent=2)

print(f'Saved to {output_file}')
