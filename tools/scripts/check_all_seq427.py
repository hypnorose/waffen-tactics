#!/usr/bin/env python3
import sys, os, random
sys.path.insert(0, 'waffen-tactics/src')
sys.path.insert(0, 'waffen-tactics-web/backend')
from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from services.combat_service import run_combat_simulation

game_data = load_game_data()
player_units = [CombatUnit(id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack, defense=u.stats.defense, attack_speed=u.stats.attack_speed, position='front' if i < 5 else 'back', stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana) for i, u in enumerate(game_data.units[:10])]
opponent_units = [CombatUnit(id=u.id, name=u.name, hp=u.stats.hp, attack=u.stats.attack, defense=u.stats.defense, attack_speed=u.stats.attack_speed, position='front' if i < 5 else 'back', stats=u.stats, skill=u.skill, max_mana=u.stats.max_mana) for i, u in enumerate(game_data.units[10:20])]
random.seed(5)
result = run_combat_simulation(player_units, opponent_units)

print("ALL events at seq 427:")
events = sorted(result['events'], key=lambda x: x[1].get('seq', 0))
for event_type, event_data in events:
    seq = event_data.get('seq')
    if seq == 427:
        print(f"Event: {event_type}")
        print(f"  attacker: {event_data.get('attacker_name', 'N/A')}")
        print(f"  target: {event_data.get('target_name', event_data.get('unit_name', 'N/A'))}")
        print(f"  damage: {event_data.get('damage', 'N/A')}")
        print(f"  target_hp: {event_data.get('target_hp', 'N/A')}")
        print(f"  is_skill: {event_data.get('is_skill', False)}")
        print()
