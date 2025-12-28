import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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


def test_dot_not_applied_to_dead_unit():
    """If a unit is already dead, DoT ticks should not be applied to it."""
    sim = CombatSimulator(dt=0.1, timeout=1)

    # Create a unit that is dead (hp 0) but has a DoT effect scheduled
    dead = CombatUnit(id='d0', name='DeadUnit', hp=0, attack=0, defense=0, attack_speed=0.0, position='front')
    dead.max_hp = 100
    dead.stats = SimpleNamespace(mana_on_attack=0)
    # Add a DoT effect as the engine would store it
    dead.effects = [{
        'type': 'damage_over_time',
        'damage': 10,
        'damage_type': 'poison',
        'interval': 1.0,
        'ticks_remaining': 3,
        'next_tick_time': 0.0,
    }]

    events = []

    def cb(et, data):
        events.append((et, data))

    # hp list indicates dead
    hp_list = [0]

    # Process DoT for team containing the dead unit at time > next_tick_time
    sim._process_dot_for_team([dead], time=0.5, log=[], event_callback=cb, side='team_a')

    types = [t for t, d in events]
    assert 'damage_over_time_tick' not in types, f"DoT tick applied to dead unit: {types}"


def test_skill_does_not_apply_effects_to_dead_target():
    """Skills targeting a dead unit should not apply their effects to that dead target."""
    gd = load_game_data()
    unit_def = next((u for u in gd.units if u.id == 'piwniczak'), None)
    assert unit_def is not None

    caster = make_combat_unit_from_unitdef(unit_def, instance_id='caster1', hp=200, max_hp=200)
    caster.mana = caster.max_mana

    # Create a dead target
    dead_target = CombatUnit(id='t_dead', name='DeadTarget', hp=0, attack=0, defense=0, attack_speed=0.0, position='front')
    dead_target.max_hp = 100
    dead_target.stats = SimpleNamespace(mana_on_attack=0)
    dead_target.effects = []

    sim = CombatSimulator(dt=0.1, timeout=1)
    sim.team_a = [caster]
    sim.team_b = [dead_target]

    events = []

    def cb(et, data):
        events.append((et, data))

    # Call internal skill processor with target already dead
    sim._process_skill_cast(caster, dead_target, time=0.5, log=[], event_callback=cb, side='team_a')

    types = [t for t, d in events]
    # We may still see mana_update/skill_cast meta events, but no actual effects targeting the dead unit
    assert 'damage_over_time_applied' not in types
    assert 'unit_stunned' not in types
    assert 'unit_attack' not in types or all(d.get('target_id') != 't_dead' for t, d in events if t == 'unit_attack')
