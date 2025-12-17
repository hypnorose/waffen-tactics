import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from waffen_tactics.services.data_loader import load_game_data
from waffen_tactics.services.combat_shared import CombatSimulator, CombatUnit
from waffen_tactics.models.skill import Skill


def make_combat_unit_from_unitdef(unit_def, instance_id='inst', hp=None, max_hp=None):
    base_stats = getattr(unit_def, 'stats', None)
    max_m = max_hp if max_hp is not None else (base_stats.hp if base_stats else unit_def.stats if hasattr(unit_def, 'stats') else 100)
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

    # Ensure max_hp attribute exists for conditional checks
    cu.max_hp = max_m
    cu.hp = cur_hp
    return cu


def test_rafcikd_conditional_low_hp_applies_shield_and_big_buff():
    gd = load_game_data()
    unit = next((u for u in gd.units if u.id == 'rafcikd'), None)
    assert unit is not None

    # Set caster HP low (below 60% threshold) so conditional branch applies
    max_hp = 200
    low_hp = int(max_hp * 0.5)  # 50%

    caster = make_combat_unit_from_unitdef(unit, instance_id='raf_inst', hp=low_hp, max_hp=max_hp)
    enemy = CombatUnit(id='dummy', name='Dummy', hp=300, attack=10, defense=5, attack_speed=1.0, position='front')

    # Embed the skill JSON as used by the game so the test is independent
    skill_json = {
        'name': 'Defensive Stance',
        'description': 'Conditional defensive skill',
        'mana_cost': 40,
        'effects': [
            {
                'type': 'conditional',
                'target': 'self',
                'condition': {'type': 'health_percentage', 'threshold': 60},
                'effects': [
                    {'type': 'shield', 'target': 'self', 'amount': 30, 'duration': 3},
                    {'type': 'buff', 'target': 'self', 'stat': 'defense', 'value': 15, 'duration': 2}
                ],
                'else_effects': [
                    {'type': 'buff', 'target': 'self', 'stat': 'defense', 'value': 10, 'duration': 2}
                ]
            }
        ]
    }

    skill_obj = Skill.from_dict(skill_json)
    caster.skill = {'effect': {'skill': skill_obj}, 'name': skill_obj.name, 'mana_cost': skill_obj.mana_cost}
    caster.mana = caster.max_mana = skill_obj.mana_cost  # force skill cast

    sim = CombatSimulator(dt=0.1, timeout=1)
    sim.team_a = [caster]
    sim.team_b = [enemy]

    events = []

    def cb(et, data):
        events.append((et, data))

    target_hp_list = [enemy.hp]
    sim._process_skill_cast(caster, enemy, target_hp_list, 0, 0.5, [], cb, 'team_a')

    types = [e[0] for e in events]
    assert 'shield_applied' in types, f"Expected shield_applied in events, got {types}"
    # stat_buff with value 15 should be present
    buffs = [d for t, d in events if t == 'stat_buff']
    assert any(b.get('value') == 15 for b in buffs), f"Expected buff value 15, buffs={buffs}"


def test_rafcikd_conditional_high_hp_applies_small_buff_only():
    gd = load_game_data()
    unit = next((u for u in gd.units if u.id == 'rafcikd'), None)
    assert unit is not None

    # Set caster HP high (above 60% threshold) so else_effects apply
    max_hp = 200
    high_hp = int(max_hp * 0.9)  # 90%

    caster = make_combat_unit_from_unitdef(unit, instance_id='raf_inst2', hp=high_hp, max_hp=max_hp)
    enemy = CombatUnit(id='dummy2', name='Dummy2', hp=300, attack=10, defense=5, attack_speed=1.0, position='front')

    # Use the same embedded skill JSON as above
    skill_json = {
        'name': 'Defensive Stance',
        'description': 'Conditional defensive skill',
        'mana_cost': 40,
        'effects': [
            {
                'type': 'conditional',
                'target': 'self',
                'condition': {'type': 'health_percentage', 'threshold': 60},
                'effects': [
                    {'type': 'shield', 'target': 'self', 'amount': 30, 'duration': 3},
                    {'type': 'buff', 'target': 'self', 'stat': 'defense', 'value': 15, 'duration': 2}
                ],
                'else_effects': [
                    {'type': 'buff', 'target': 'self', 'stat': 'defense', 'value': 10, 'duration': 2}
                ]
            }
        ]
    }

    skill_obj = Skill.from_dict(skill_json)
    caster.skill = {'effect': {'skill': skill_obj}, 'name': skill_obj.name, 'mana_cost': skill_obj.mana_cost}
    caster.mana = caster.max_mana = skill_obj.mana_cost  # force skill cast

    sim = CombatSimulator(dt=0.1, timeout=1)
    sim.team_a = [caster]
    sim.team_b = [enemy]

    events = []

    def cb(et, data):
        events.append((et, data))

    target_hp_list = [enemy.hp]
    sim._process_skill_cast(caster, enemy, target_hp_list, 0, 0.5, [], cb, 'team_a')

    types = [e[0] for e in events]
    # No shield when HP high
    assert 'shield_applied' not in types
    buffs = [d for t, d in events if t == 'stat_buff']
    assert any(b.get('value') == 10 for b in buffs), f"Expected buff value 10, buffs={buffs}"
