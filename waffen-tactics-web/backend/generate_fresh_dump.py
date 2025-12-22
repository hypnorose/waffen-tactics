#!/usr/bin/env python3
"""Generate fresh combat dump with shield units to test effect_id fix."""
import sys
import random
import json
sys.path.insert(0, '../../waffen-tactics/src')

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation

# Load game data
game_data = load_game_data()

# Find Srebrna Gwardia (has shield skill)
srebrna = next((u for u in game_data.units if 'srebrna' in u.id.lower()), None)
if not srebrna:
    print("WARNING: Could not find Srebrna Gwardia")
    srebrna = game_data.units[0]

# Build player team with shield units
p_units = []
for i in range(4):
    p_units.append(CombatUnit(
        id=f'p_{i}',
        name=srebrna.name,
        hp=srebrna.stats.hp * 2,  # 2-star
        attack=srebrna.stats.attack * 2,
        defense=srebrna.stats.defense * 2,
        attack_speed=srebrna.stats.attack_speed,
        position='front',
        stats=srebrna.stats,
        skill=srebrna.skill,
        max_mana=srebrna.stats.max_mana,
        star_level=2
    ))

# Build opponent team
random.seed(42)
opponent_ids = random.sample([u.id for u in game_data.units], 4)
o_units = []
for i, uid in enumerate(opponent_ids):
    u = next(unit for unit in game_data.units if unit.id == uid)
    o_units.append(CombatUnit(
        id=f'o_{i}',
        name=u.name,
        hp=u.stats.hp,
        attack=u.stats.attack,
        defense=u.stats.defense,
        attack_speed=u.stats.attack_speed,
        position='front' if i < 2 else 'back',
        stats=u.stats,
        skill=u.skill,
        max_mana=u.stats.max_mana,
        star_level=1
    ))

print(f"Player team: {[u.name for u in p_units]}")
print(f"Opponent team: {[u.name for u in o_units]}")
print()

# Run combat
result = run_combat_simulation(p_units, o_units)
events = result['events']

# Convert to standard format
all_events = []
for event_type, data in events:
    event = {'type': event_type, **data}
    all_events.append(event)

print(f"Combat finished. Events: {len(all_events)}")

# Count shield_applied events
shield_events = [e for e in all_events if e.get('type') == 'shield_applied']
print(f"Shield events: {len(shield_events)}")

# Check if they have effect_id
missing_ids = [e for e in shield_events if not e.get('effect_id')]
print(f"Shield events missing effect_id: {len(missing_ids)}")

if missing_ids:
    print("❌ WARNING: Shield events still missing effect_id!")
    print("First missing:", missing_ids[0])
else:
    print("✅ All shield events have effect_id!")

# Save to file
with open('events_test_fresh.json', 'w') as f:
    json.dump(all_events, f, indent=2)

print(f"✓ Saved to events_test_fresh.json")
