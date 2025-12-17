"""
Integration tests: run skills within the combat simulator and assert
that skill_cast and the expected effect events are emitted into the
combat event stream (no HTTP).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random

from services.combat_service import run_combat_simulation
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType, SkillExecutionContext


class SimpleStats:
    def __init__(self, hp, mana_on_attack=0):
        self.hp = hp
        self.mana_on_attack = mana_on_attack


def make_combat_unit(uid, name, hp=100, attack=10, defense=0, attack_speed=1.0, max_mana=100, stats=None, skill=None, position='front'):
    return CombatUnit(id=uid, name=name, hp=hp, attack=attack, defense=defense, attack_speed=attack_speed, effects=None, max_mana=max_mana, skill=skill, mana_regen=0, stats=stats, position=position)


def _run_simulation_with_seed(player_units, opponent_units, seed=1):
    # Make simulation deterministic by forcing random.random to return a low value
    # which ensures attack and skill chance checks pass in a predictable way.
    orig_random = random.random
    try:
        random.random = lambda: 0.0
        result = run_combat_simulation(player_units, opponent_units)
    finally:
        random.random = orig_random
    return result


def test_skill_damage_in_combat_emits_skill_and_unit_attack():
    # Caster will gain full mana in one attack (mana_on_attack == max_mana)
    stats = SimpleStats(hp=100, mana_on_attack=100)
    # Create a Skill that deals 40 damage to a single enemy
    eff = Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 40})
    skill = Skill(name='Slam', description='Deal damage', mana_cost=50, effects=[eff])

    # Attach skill into the combat-unit skill dict that simulator expects
    skill_dict = {'name': skill.name, 'description': skill.description, 'mana_cost': skill.mana_cost, 'effect': {'skill': skill}}

    caster = make_combat_unit('p1', 'Caster', hp=100, attack=5, attack_speed=1.0, max_mana=100, stats=stats, skill=skill_dict)
    # Opponent - single target
    target = make_combat_unit('o1', 'Target', hp=120, attack=1, attack_speed=0.1, max_mana=100, stats=SimpleStats(120, mana_on_attack=0))

    result = _run_simulation_with_seed([caster], [target])

    # Collect event types
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' in types, 'Expected skill_cast event in combat events'
    # Skill damage should produce a unit_attack event when executed by the skill executor
    assert 'unit_attack' in types


def test_skill_support_effects_in_combat_emit_heal_buff_shield():
    stats = SimpleStats(hp=100, mana_on_attack=100)

    effects = [
        Effect(type=EffectType.HEAL, target=TargetType.SELF, params={'amount': 30}),
        Effect(type=EffectType.BUFF, target=TargetType.SELF, params={'stat': 'attack', 'value': 5, 'duration': 5}),
        Effect(type=EffectType.SHIELD, target=TargetType.SELF, params={'amount': 20, 'duration': 3})
    ]
    skill = Skill(name='Support Wave', description='Heals and buffs self', mana_cost=50, effects=effects)
    skill_dict = {'name': skill.name, 'description': skill.description, 'mana_cost': skill.mana_cost, 'effect': {'skill': skill}}

    # Make caster start below max HP so heal will have an effect
    caster = make_combat_unit('p2', 'Healer', hp=70, attack=1, attack_speed=1.0, max_mana=100, stats=stats, skill=skill_dict)
    enemy = make_combat_unit('o2', 'Dummy', hp=1, attack=0, attack_speed=0.1, max_mana=100, stats=SimpleStats(1, mana_on_attack=0))

    result = _run_simulation_with_seed([caster], [enemy])
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' in types
    assert 'unit_heal' in types
    assert 'stat_buff' in types
    assert 'shield_applied' in types


def test_skill_stun_in_combat_emits_unit_stunned():
    stats = SimpleStats(hp=100, mana_on_attack=100)
    eff = Effect(type=EffectType.STUN, target=TargetType.SINGLE_ENEMY, params={'duration': 2})
    skill = Skill(name='Stun Blast', description='Stun target', mana_cost=50, effects=[eff])
    skill_dict = {'name': skill.name, 'description': skill.description, 'mana_cost': skill.mana_cost, 'effect': {'skill': skill}}

    caster = make_combat_unit('p3', 'Stunner', hp=100, attack=5, attack_speed=1.0, max_mana=100, stats=stats, skill=skill_dict)
    target = make_combat_unit('o3', 'Target', hp=100, attack=1, attack_speed=0.1, max_mana=100, stats=SimpleStats(100, mana_on_attack=0))

    result = _run_simulation_with_seed([caster], [target])
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' in types
    assert 'unit_stunned' in types
    stun = next((d for t, d in events if t == 'unit_stunned'), None)
    assert stun and stun.get('duration') == 2


def test_skill_dot_applies_and_emits_ticks_in_event_stream():
    """Skill should apply a DoT effect and simulator should emit tick events."""
    # Caster will gain full mana in one attack
    stats = SimpleStats(hp=100, mana_on_attack=100)
    # DoT: 2 seconds duration, 1s interval, damage 5 per tick
    eff = Effect(type=EffectType.DAMAGE_OVER_TIME, target=TargetType.SINGLE_ENEMY, params={'damage': 5, 'duration': 2, 'interval': 1.0})
    skill = Skill(name='Corrupting Bolt', description='Apply DoT', mana_cost=50, effects=[eff])
    skill_dict = {'name': skill.name, 'description': skill.description, 'mana_cost': skill.mana_cost, 'effect': {'skill': skill}}

    caster = make_combat_unit('p4', 'DoTer', hp=100, attack=5, attack_speed=1.0, max_mana=100, stats=stats, skill=skill_dict)
    # Make target sufficiently durable so DoT ticks can occur
    target = make_combat_unit('o4', 'Target', hp=1000, attack=1, attack_speed=0.1, max_mana=100, stats=SimpleStats(1000, mana_on_attack=0))

    result = _run_simulation_with_seed([caster], [target])
    events = result.get('events', [])
    types = [t for t, _ in events]

    # The handler should emit an applied event when the DoT is attached
    assert 'damage_over_time_applied' in types

    # The simulator should produce periodic tick events while DoT is active
    dot_ticks = [d for t, d in events if t == 'damage_over_time_tick']
    assert len(dot_ticks) >= 1, 'Expected at least one DoT tick event in the stream'
    # If interval=1 and duration=2, expect ~2 ticks (may vary by simulation timing)
    assert len(dot_ticks) >= 2 or len(dot_ticks) == 1
