#!/usr/bin/env python3
"""Debug script for seed 205 HP desync"""
import sys
import random
sys.path.insert(0, '../../waffen-tactics/src')

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import run_combat_simulation
from services.combat_event_reconstructor import CombatEventReconstructor

# Load game data
game_data = load_game_data()

random.seed(205)
all_ids = [u.id for u in game_data.units]
sample = random.sample(all_ids, 20)

def get_unit(uid):
    return next(u for u in game_data.units if u.id == uid)

# Build teams
p_units = []
for uid in sample[:10]:
    u = get_unit(uid)
    p_units.append(CombatUnit(
        id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack,
        defense=u.stats.defense, attack_speed=u.stats.attack_speed,
        position='front' if len(p_units) < 5 else 'back',
        stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana
    ))

o_units = []
for uid in sample[10:]:
    u = get_unit(uid)
    o_units.append(CombatUnit(
        id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack,
        defense=u.stats.defense, attack_speed=u.stats.attack_speed,
        position='front' if len(o_units) < 5 else 'back',
        stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana
    ))

print(f"Player team: {[u.name for u in p_units]}")
print(f"Opponent team: {[u.name for u in o_units]}")
print()

# Run combat
result = run_combat_simulation(p_units, o_units)
events = result['events']
events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] == 'state_snapshot' else 1, x[1]['timestamp']))

# Find all events for mrozu
mrozu_events = [(etype, p) for etype, p in events if 'mrozu' in str(p.get('unit_id', '')).lower() or 'mrozu' in str(p.get('unit_name', '')).lower()]
print(f"Total events mentioning mrozu: {len(mrozu_events)}")
print()

# Show heal and death events
heal_events = [(etype, p) for etype, p in mrozu_events if etype in ['heal', 'unit_heal']]
death_events = [(etype, p) for etype, p in mrozu_events if etype == 'unit_died']
print(f"Heal events for mrozu: {len(heal_events)}")
for i, (etype, p) in enumerate(heal_events[:10]):
    print(f"  [{i}] {etype} seq={p.get('seq')}: healer={p.get('healer_id', p.get('source_id'))}, target={p.get('unit_id')}, unit_hp={p.get('unit_hp')}, pre_hp={p.get('pre_hp')}, post_hp={p.get('post_hp')}, amount={p.get('amount')}")
print()
print(f"Death events for mrozu: {len(death_events)}")
for i, (etype, p) in enumerate(death_events):
    print(f"  [{i}] {etype} seq={p.get('seq')}")
print()

# Run reconstructor
reconstructor = CombatEventReconstructor()
state_snapshots = [e for e in events if e[0] == 'state_snapshot']
if state_snapshots:
    reconstructor.initialize_from_snapshot(state_snapshots[0][1])

# Process all events with debug output for mrozu heals
for event_type, event_data in events:
    if event_type in ['heal', 'unit_heal'] and 'mrozu' in str(event_data.get('unit_id', '')).lower():
        unit_id = event_data.get('unit_id')
        # Get current HP before processing
        u_dict = reconstructor._get_unit_dict(unit_id)
        old_hp = u_dict['hp'] if u_dict else None

    reconstructor.process_event(event_type, event_data)

    if event_type in ['heal', 'unit_heal'] and 'mrozu' in str(event_data.get('unit_id', '')).lower():
        # Get HP after processing
        u_dict = reconstructor._get_unit_dict(unit_id)
        new_hp = u_dict['hp'] if u_dict else None
        print(f"Processed {event_type} seq={event_data.get('seq')}: {old_hp} -> {new_hp} (event unit_hp={event_data.get('unit_hp')}, post_hp={event_data.get('post_hp')})")

# Final state
p_recon_dict, o_recon_dict = reconstructor.get_reconstructed_state()
print()
print("Reconstructed player units (dict keys):", list(p_recon_dict.keys()))
mrozu_final = next((p_recon_dict[k] for k in p_recon_dict if 'mrozu' in k.lower()), None)
print(f"Final mrozu HP (reconstructor): {mrozu_final['hp'] if mrozu_final else 'NOT FOUND'}")

# Check combat result
print(f"Winner: {result.get('winner')}")
print(f"Team A survivors: {result.get('team_a_survivors')}, Team B survivors: {result.get('team_b_survivors')}")
print("Simulation survivors:", [(u.get('id'), u.get('hp')) for u in result.get('survivors', [])])
for u in result.get('survivors', []):
    if 'mrozu' in u.get('id', '').lower():
        print(f"Final mrozu HP (simulation): {u['hp']}")

# Check original unit object HP (after simulation mutated it)
mrozu_unit = next((u for u in p_units if 'mrozu' in u.id.lower()), None)
print(f"Original p_units mrozu HP (after simulation): {mrozu_unit.hp if mrozu_unit else 'NOT FOUND'}")

# Check all player units
print("\nAll player units HP after simulation:")
for u in p_units:
    print(f"  {u.id}: {u.hp}")
