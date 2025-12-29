"""
Tests for the new skill executor and effect handlers.

These tests call `skill_executor.execute_skill` directly (no HTTP) and
assert that the returned events include the expected effect events and
fields such as `is_skill` for damage events.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType, SkillExecutionContext
from waffen_tactics.services.skill_executor import skill_executor
from waffen_tactics.services.combat_unit import CombatUnit


class SimpleStats:
    def __init__(self, hp, mana_on_attack=0):
        self.hp = hp
        self.mana_on_attack = mana_on_attack


def make_unit(uid, name, hp=100, max_mana=100):
    stats = SimpleStats(hp, mana_on_attack=0)
    return CombatUnit(id=uid, name=name, hp=hp, attack=10, defense=0, attack_speed=1.0, max_mana=max_mana, stats=stats)


def test_skill_damage_emits_unit_attack_and_is_skill():
    caster = make_unit('c1', 'Caster', hp=100, max_mana=100)
    target = make_unit('t1', 'Target', hp=120)

    # Give caster enough mana
    caster.mana = 100

    # Skill: single enemy damage of 40
    eff = Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 40})
    skill = Skill(name='Slam', description='Deal damage', mana_cost=50, effects=[eff])

    ctx = SkillExecutionContext(caster=caster, team_a=[caster], team_b=[target], combat_time=1.0)

    events = skill_executor.execute_skill(skill, ctx)

    # Expect mana_update, unit_attack, skill_cast in events
    types = [t for t, _ in events]
    assert 'mana_update' in types
    assert 'unit_attack' in types
    assert 'skill_cast' in types

    # Find unit_attack event and verify is_skill and damage
    ua = next((data for t, data in events if t == 'unit_attack'), None)
    assert ua is not None
    assert ua.get('applied_damage') == 40
    assert ua.get('is_skill') is True


def test_skill_heal_buff_and_shield_emit_events():
    caster = make_unit('c2', 'Healer', hp=100, max_mana=100)
    ally = make_unit('a1', 'Ally', hp=10, max_mana=100)
    # Ensure ally has room to be healed (max_hp larger than current hp)
    ally.max_hp = 100
    ally._set_hp(10, caller_module='event_canonicalizer')
    enemy = make_unit('e1', 'Enemy', hp=100, max_mana=100)

    caster.mana = 100

    effects = [
        Effect(type=EffectType.HEAL, target=TargetType.ALLY_TEAM, params={'amount': 30}),
        Effect(type=EffectType.BUFF, target=TargetType.ALLY_TEAM, params={'stat': 'attack', 'value': 5, 'duration': 5}),
        Effect(type=EffectType.SHIELD, target=TargetType.ALLY_TEAM, params={'amount': 20, 'duration': 3})
    ]

    skill = Skill(name='Support Wave', description='Heals and buffs allies', mana_cost=50, effects=effects)
    ctx = SkillExecutionContext(caster=caster, team_a=[caster, ally], team_b=[enemy], combat_time=2.0)

    events = skill_executor.execute_skill(skill, ctx)
    types = [t for t, _ in events]

    assert 'mana_update' in types
    assert 'unit_heal' in types
    assert 'stat_buff' in types
    assert 'shield_applied' in types
    assert 'skill_cast' in types

    # Check payloads contain expected fields
    heal = next((d for t, d in events if t == 'unit_heal'), None)
    assert heal and heal.get('amount') == 30

    buff = next((d for t, d in events if t == 'stat_buff'), None)
    assert buff and buff.get('stat') == 'attack' and buff.get('value') == 5

    shield = next((d for t, d in events if t == 'shield_applied'), None)
    assert shield and shield.get('amount') == 20


def test_skill_stun_emits_unit_stunned():
    caster = make_unit('s1', 'Stunner', hp=100, max_mana=100)
    target = make_unit('s2', 'Victim', hp=100, max_mana=100)

    caster.mana = 100

    eff = Effect(type=EffectType.STUN, target=TargetType.SINGLE_ENEMY, params={'duration': 2})
    skill = Skill(name='Stunner', description='Stun target', mana_cost=50, effects=[eff])
    ctx = SkillExecutionContext(caster=caster, team_a=[caster], team_b=[target], combat_time=3.0)

    events = skill_executor.execute_skill(skill, ctx)
    types = [t for t, _ in events]

    assert 'unit_stunned' in types
    stun = next((d for t, d in events if t == 'unit_stunned'), None)
    assert stun and stun.get('duration') == 2
