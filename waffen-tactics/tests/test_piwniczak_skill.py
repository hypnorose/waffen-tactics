import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from types import SimpleNamespace

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit


def make_combat_unit_from_unitdef(unit_def, instance_id='inst', hp=None, max_hp=None):
    base_stats = getattr(unit_def, 'stats', None)
    max_m = max_hp if max_hp is not None else (base_stats.hp if base_stats else getattr(unit_def, 'max_mana', 100))
    cur_hp = hp if hp is not None else max_m

    cu = CombatUnit(
        id=instance_id,
        name=unit_def.name,
        hp=cur_hp,
        attack=unit_def.stats.attack if hasattr(unit_def.stats, 'attack') else 10,
        defense=unit_def.stats.defense if hasattr(unit_def.stats, 'defense') else 0,
        attack_speed=unit_def.stats.attack_speed if hasattr(unit_def.stats, 'attack_speed') else 1.0,
        position='front',
        max_mana=getattr(unit_def.stats, 'max_mana', getattr(unit_def, 'max_mana', 100)),
        stats=unit_def.stats,
        skill={
            'name': unit_def.skill.name,
            'description': unit_def.skill.description,
            'mana_cost': unit_def.skill.mana_cost,
            'effect': unit_def.skill.effect
        } if hasattr(unit_def, 'skill') and unit_def.skill else None
    )

    cu.max_hp = max_m
    cu.hp = cur_hp
    return cu


def test_piwniczak_stun_and_dot_applied_events():
    gd = load_game_data()
    unit = next((u for u in gd.units if u.id == 'piwniczak'), None)
    assert unit is not None

    caster = make_combat_unit_from_unitdef(unit, instance_id='d1', hp=200, max_hp=200)
    target_def = next((u for u in gd.units if u.id == 't1'), None)
    # If no 't1' in data, create a dummy target
    enemy = CombatUnit(id='t1', name='Tank', hp=1000, attack=10, defense=10, attack_speed=1.0, position='front')

    caster.mana = caster.max_mana

    sim = CombatSimulator(dt=0.1, timeout=5)
    sim.team_a = [caster]
    sim.team_b = [enemy]

    events = []

    def cb(et, data):
        events.append((et, data))

    sim._process_skill_cast(caster, enemy, time=0.2, log=[], event_callback=cb, side='team_a')

    # After skill cast we should have a stun event and a damage_over_time_applied
    types = [t for t, d in events]
    assert 'unit_stunned' in types, f"Expected unit_stunned in events, got {types}"
    assert 'damage_over_time_applied' in types, f"Expected damage_over_time_applied in events, got {types}"

    # Check fields present
    dot_events = [d for t, d in events if t == 'damage_over_time_applied']
    assert dot_events and all(e.get('unit_name') and e.get('caster_name') for e in dot_events)


def test_piwniczak_dot_ticks_and_death_event():
    gd = load_game_data()
    unit = next((u for u in gd.units if u.id == 'piwniczak'), None)
    assert unit is not None

    caster = make_combat_unit_from_unitdef(unit, instance_id='d1', hp=200, max_hp=200)
    # Make a fragile target so DoT can be observed and possibly kill
    enemy = CombatUnit(id='tfrag', name='FragTank', hp=50, attack=1, defense=0, attack_speed=1.0, position='front')
    # Ensure stats exist to avoid attribute errors (e.g., mana_on_attack)
    enemy.stats = SimpleNamespace(mana_on_attack=0)

    caster.mana = caster.max_mana

    sim = CombatSimulator(dt=0.1, timeout=6)
    sim.team_a = [caster]
    sim.team_b = [enemy]

    collected = []

    def cb(et, data):
        collected.append((et, data))

    result = sim.simulate(sim.team_a, sim.team_b, cb)

    types = [t for t, d in collected]
    # We expect at least one damage_over_time_tick or a death (both are valid outcomes)
    assert 'damage_over_time_tick' in types or 'unit_died' in types, f"Expected damage_over_time_tick or unit_died in collected, got {types}"
    # If death happened, ensure unit_died includes unit_name
    deaths = [d for t, d in collected if t == 'unit_died']
    if deaths:
        assert all(d.get('unit_name') for d in deaths)
