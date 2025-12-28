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

print("Events from seq 410-435:")
events = sorted(result['events'], key=lambda x: x[1].get('seq', 0))
for event_type, event_data in events:
    seq = event_data.get('seq')
    if seq and 410 <= seq <= 435:
        if event_data.get('target_name') == 'OperatorKosiarki' or event_data.get('unit_name') == 'OperatorKosiarki':
            print(f"seq={seq:3d} {event_type:15s} target={event_data.get('target_name', event_data.get('unit_name', '?')):20s} ", end='')
            if event_type in ['attack', 'unit_attack']:
                print(f"attacker={event_data.get('attacker_name', '?'):15s} damage={event_data.get('damage', 0):3d} target_hp={event_data.get('target_hp', '?')}")
            elif event_type == 'unit_heal':
                print(f"healer={event_data.get('healer_name', '?'):15s} heal={event_data.get('heal_amount', 0):3d} unit_hp={event_data.get('unit_hp', '?')}")
            else:
                print()
