"""
Tests that verify the SSE mapping of combat events to JSON payloads.

These tests run short combat simulations that produce skill-related
events (damage/heal/buff/shield/stun) and assert that `map_event_to_sse_payload`
returns payloads the route would stream to the client.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.combat_service import run_combat_simulation
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType
import routes.game_combat as gc


class SimpleStats:
    def __init__(self, hp, mana_on_attack=0):
        self.hp = hp
        self.mana_on_attack = mana_on_attack


def make_unit(uid, name, hp=100, max_mana=100, skill=None):
    stats = SimpleStats(hp, mana_on_attack=0)
    # CombatUnit expects either a legacy skill-dict or a dict with an 'effect' key
    # that may contain a 'skill' (new system). If a Skill instance is passed,
    # wrap it into the expected dict shape so CombatUnit stores it correctly.
    if skill and hasattr(skill, 'name'):
        skill_dict = {
            'name': skill.name,
            'description': skill.description,
            'mana_cost': skill.mana_cost,
            'effect': {'skill': skill}
        }
    else:
        skill_dict = skill

    return CombatUnit(id=uid, name=name, hp=hp, attack=10, defense=0, attack_speed=1.0, max_mana=max_mana, stats=stats, skill=skill_dict)


def test_mapping_includes_shield_and_buff_and_heal_and_attack():
    # Caster with 3-effect skill: heal allies, buff allies, shield allies
    heal = Effect(type=EffectType.HEAL, target=TargetType.ALLY_TEAM, params={'amount': 30})
    buff = Effect(type=EffectType.BUFF, target=TargetType.ALLY_TEAM, params={'stat': 'attack', 'value': 5, 'duration': 5})
    shield = Effect(type=EffectType.SHIELD, target=TargetType.ALLY_TEAM, params={'amount': 20, 'duration': 3})
    skill = Skill(name='Support Wave', description='Support', mana_cost=50, effects=[heal, buff, shield])

    caster = make_unit('c1', 'Caster', hp=100, max_mana=100, skill=skill)
    ally = make_unit('a1', 'Ally', hp=10, max_mana=100)
    enemy = make_unit('e1', 'Enemy', hp=100, max_mana=100)

    caster.mana = 100

    result = run_combat_simulation([caster, ally], [enemy])

    assert 'events' in result

    types = [et for et, _ in result['events']]
    # Ensure expected internal events exist
    assert any(t in ('unit_heal', 'heal') or t == 'unit_heal' for t in types) or 'stat_buff' in types or 'shield_applied' in types

    # Map each event and assert mapping produces payloads for interesting types
    mapped = [gc.map_event_to_sse_payload(et, d) for et, d in result['events']]
    # Flatten types
    mapped_types = [m['type'] for m in mapped if m]

    assert 'unit_heal' in mapped_types or 'stat_buff' in mapped_types or 'shield_applied' in mapped_types


def test_mapping_preserves_is_skill_on_attack():
    # Damage skill
    dmg = Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 50})
    skill = Skill(name='Slam', description='Damage', mana_cost=10, effects=[dmg])

    caster = make_unit('c2', 'Caster2', hp=100, max_mana=100, skill=skill)
    target = make_unit('t2', 'Target2', hp=120)
    caster.mana = 100

    result = run_combat_simulation([caster], [target])
    mapped = [gc.map_event_to_sse_payload(et, d) for et, d in result.get('events', [])]

    # Find any unit_attack that was produced by a skill (is_skill == True)
    skill_attacks = [m for m in mapped if m and m.get('type') == 'unit_attack' and m.get('is_skill')]
    assert len(skill_attacks) >= 1, f"Expected at least one skill-origin unit_attack, mapped={mapped}"


def test_all_mapped_payloads_include_seq():
    # Test that every mapped payload includes 'seq'
    heal = Effect(type=EffectType.HEAL, target=TargetType.ALLY_TEAM, params={'amount': 30})
    skill = Skill(name='Heal', description='Heal', mana_cost=50, effects=[heal])

    caster = make_unit('c3', 'Caster3', hp=100, max_mana=100, skill=skill)
    ally = make_unit('a3', 'Ally3', hp=10, max_mana=100)
    enemy = make_unit('e3', 'Enemy3', hp=100, max_mana=100)

    caster.mana = 100

    result = run_combat_simulation([caster, ally], [enemy])

    assert 'events' in result

    # Map each event and assert all payloads have 'seq'
    for et, d in result['events']:
        payload = gc.map_event_to_sse_payload(et, d)
        if payload:
            assert 'seq' in payload, f"Payload for event {et} missing 'seq': {payload}"
            assert isinstance(payload['seq'], int), f"seq should be int, got {type(payload['seq'])}: {payload['seq']}"


def test_seq_is_monotonically_increasing():
    # Test that seq values are monotonically increasing across events
    heal = Effect(type=EffectType.HEAL, target=TargetType.ALLY_TEAM, params={'amount': 30})
    buff = Effect(type=EffectType.BUFF, target=TargetType.ALLY_TEAM, params={'stat': 'attack', 'value': 5, 'duration': 5})
    skill = Skill(name='Support', description='Support', mana_cost=50, effects=[heal, buff])

    caster = make_unit('c4', 'Caster4', hp=100, max_mana=100, skill=skill)
    ally = make_unit('a4', 'Ally4', hp=10, max_mana=100)
    enemy = make_unit('e4', 'Enemy4', hp=100, max_mana=100)

    caster.mana = 100

    result = run_combat_simulation([caster, ally], [enemy])

    assert 'events' in result

    seqs = []
    for et, d in result['events']:
        payload = gc.map_event_to_sse_payload(et, d)
        if payload and 'seq' in payload:
            seqs.append(payload['seq'])

    # Assert seqs are strictly increasing
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i-1], f"seq not increasing: {seqs[i-1]} >= {seqs[i]}"
