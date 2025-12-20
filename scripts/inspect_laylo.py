import sys
import os
# ensure local package is importable
sys.path.insert(0, os.path.join(os.getcwd(), 'waffen-tactics', 'src'))
# also add backend services path so we can import run_combat_simulation
sys.path.insert(0, os.path.join(os.getcwd(), 'waffen-tactics-web', 'backend'))
from services.combat_service import run_combat_simulation
from tests.test_combat_service import load_game_data
from waffen_tactics.services.combat_shared import CombatUnit
import random

random.seed(12345)
game_data = load_game_data()
player_unit_ids = [u.id for u in game_data.units[:10]]
opponent_unit_ids = [u.id for u in game_data.units[10:20]]

def get_unit(unit_id):
    return next(u for u in game_data.units if u.id == unit_id)

player_units = []
for unit_id in player_unit_ids:
    unit = get_unit(unit_id)
    player_units.append(CombatUnit(
        id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
        defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
        position='front' if len(player_units) < 5 else 'back',
        stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
    ))

opponent_units = []
for unit_id in opponent_unit_ids:
    unit = get_unit(unit_id)
    opponent_units.append(CombatUnit(
        id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
        defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
        position='front' if len(opponent_units) < 5 else 'back',
        stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
    ))

res = run_combat_simulation(player_units, opponent_units)
events = res['events']
events.sort(key=lambda x: (x[1].get('timestamp', 0), x[1].get('seq', 0)))

for t,d in events:
    seq = d.get('seq')
    if seq and 240 <= seq <= 280:
        print(f"EVENT seq={seq} type={t} ts={d.get('timestamp')} unit_id={d.get('unit_id') or d.get('target_id')}")
        if t == 'state_snapshot':
            # print laylo snapshot
            pl = [u for u in d['player_units'] if u['id']=='laylo']
            op = [u for u in d['opponent_units'] if u['id']=='laylo']
            if pl:
                print('  player_snapshot laylo effects=', pl[0].get('effects'))
            if op:
                print('  opponent_snapshot laylo effects=', op[0].get('effects'))

print('DONE')
