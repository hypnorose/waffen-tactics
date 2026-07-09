"""Integration tests for combat events (no HTTP).

The current ruleset disables skills, so these tests focus on attack-only
streams and the extra hit granted at full mana.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random

from services.combat_service import run_combat_simulation
from waffen_tactics.services.combat_unit import CombatUnit


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


def test_full_mana_produces_bonus_attack_and_no_skill_cast():
    stats = SimpleStats(hp=100, mana_on_attack=0)

    caster = make_combat_unit('p1', 'Caster', hp=100, attack=5, attack_speed=1.0, max_mana=100, stats=stats)
    target = make_combat_unit('o1', 'Target', hp=300, attack=1, attack_speed=0.1, max_mana=100, stats=SimpleStats(300, mana_on_attack=0))
    caster.mana = caster.max_mana

    result = _run_simulation_with_seed([caster], [target])
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' not in types
    assert types.count('unit_attack') >= 2


def test_basic_attack_stream_keeps_names():
    stats = SimpleStats(hp=100, mana_on_attack=0)

    caster = make_combat_unit('p2', 'Healer', hp=70, attack=12, attack_speed=1.0, max_mana=100, stats=stats)
    enemy = make_combat_unit('o2', 'Dummy', hp=1, attack=0, attack_speed=0.1, max_mana=100, stats=SimpleStats(1, mana_on_attack=0))

    result = _run_simulation_with_seed([caster], [enemy])
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' not in types
    assert 'unit_attack' in types
    assert any(d.get('attacker_name') for t, d in events if t == 'unit_attack')
    assert any(d.get('target_name') for t, d in events if t == 'unit_attack')


def test_full_mana_stream_has_no_skill_events():
    stats = SimpleStats(hp=100, mana_on_attack=0)

    caster = make_combat_unit('p3', 'Stunner', hp=100, attack=5, attack_speed=1.0, max_mana=100, stats=stats)
    target = make_combat_unit('o3', 'Target', hp=150, attack=1, attack_speed=0.1, max_mana=100, stats=SimpleStats(150, mana_on_attack=0))
    caster.mana = caster.max_mana

    result = _run_simulation_with_seed([caster], [target])
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' not in types
    assert types.count('unit_attack') >= 2


def test_bonus_attack_resets_mana_to_zero():
    stats = SimpleStats(hp=100, mana_on_attack=0)
    caster = make_combat_unit('p4', 'DoTer', hp=100, attack=5, attack_speed=1.0, max_mana=100, stats=stats)
    target = make_combat_unit('o4', 'Target', hp=1000, attack=1, attack_speed=0.1, max_mana=100, stats=SimpleStats(1000, mana_on_attack=0))
    caster.mana = caster.max_mana

    result = _run_simulation_with_seed([caster], [target])
    events = result.get('events', [])
    types = [t for t, _ in events]

    assert 'skill_cast' not in types
    assert caster.mana == 0
