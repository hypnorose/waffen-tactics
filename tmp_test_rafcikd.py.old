import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'waffen-tactics', 'src'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit


def stat_val(stats_obj, key, default):
    try:
        if isinstance(stats_obj, dict):
            return stats_obj.get(key, default)
        return getattr(stats_obj, key, default)
    except Exception:
        return default


def main():
    gd = load_game_data()
    unit = next((u for u in gd.units if u.id == 'rafcikd'), None)
    if not unit:
        print('rafcikd not found in game data')
        return

    base_stats = getattr(unit, 'stats', None)
    hp = int(stat_val(base_stats, 'hp', 200))
    attack = int(stat_val(base_stats, 'attack', 30))
    defense = int(stat_val(base_stats, 'defense', 10))
    attack_speed = float(stat_val(base_stats, 'attack_speed', 1.0))
    max_mana = int(stat_val(base_stats, 'max_mana', getattr(unit, 'max_mana', 100)))

    # Build CombatUnit for caster using prepared shape used by combat_service
    caster = CombatUnit(
        id='raf_inst',
        name=unit.name,
        hp=hp,
        attack=attack,
        defense=defense,
        attack_speed=attack_speed,
        position='front',
        max_mana=max_mana,
        stats=base_stats,
        skill={
            'name': unit.skill.name,
            'description': unit.skill.description,
            'mana_cost': unit.skill.mana_cost,
            'effect': unit.skill.effect
        } if hasattr(unit, 'skill') and unit.skill else None
    )

    # Enemy
    enemy = CombatUnit(
        id='dummy_1',
        name='Dummy',
        hp=300,
        attack=10,
        defense=5,
        attack_speed=1.0,
        position='front',
        max_mana=100,
        stats=None
    )

    # Force caster to have full mana so skill triggers
    caster.mana = caster.max_mana

    sim = CombatSimulator(dt=0.1, timeout=10)
    sim.team_a = [caster]
    sim.team_b = [enemy]

    events = []
    log = []

    def event_cb(et, data):
        print('EVENT ->', et, data)
        events.append((et, data))

    # target_hp_list matching sim._process_skill_cast expectations
    target_hp_list = [enemy.hp]

    print('Before skill call: caster.mana=', caster.mana, 'enemy_hp=', target_hp_list[0])
    sim._process_skill_cast(caster, enemy, target_hp_list, 0, 0.5, log, event_cb, 'team_a')
    print('After skill call: caster.mana=', caster.mana, 'enemy_hp=', target_hp_list[0])
    print('\nLog entries:')
    for l in log:
        print('-', l)

    print('\nCollected events:')
    for e in events:
        print(e)


if __name__ == '__main__':
    main()
