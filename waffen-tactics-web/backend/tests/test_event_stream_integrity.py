"""
Tests to ensure mapped SSE payloads include human-readable names
and required fields so the UI doesn't display `null` in messages.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.combat_service import (
    _validate_attack_animation_outcomes,
    run_combat_simulation,
)
from waffen_tactics.services.combat_errors import CombatExecutionError
from waffen_tactics.services.combat_unit import CombatUnit
import routes.game_combat as gc


class SimpleStats:
    def __init__(self, hp, mana_on_attack=0):
        self.hp = hp
        self.mana_on_attack = mana_on_attack


def make_unit(uid, name, hp=100, max_hp=None, max_mana=100, skill=None):
    # Allow tests to specify a separate max_hp (current hp vs max)
    if max_hp is None:
        max_hp = hp
    stats = SimpleStats(max_hp, mana_on_attack=0)
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


def _mapped_events_from_sim(player_units, opponent_units):
    result = run_combat_simulation(player_units, opponent_units)
    events = result.get('events', [])
    mapped = [gc.map_event_to_sse_payload(et, d) for et, d in events]
    # filter out None mappings
    return [m for m in mapped if m]


def test_attack_payloads_keep_names_and_skip_skills():
    caster = make_unit('u1', 'Piwniczak', hp=200, max_mana=150)
    target = make_unit('u2', 'V7', hp=200)
    caster.mana = 150

    mapped = _mapped_events_from_sim([caster], [target])

    attacks = [m for m in mapped if m.get('type') == 'unit_attack']
    skills = [m for m in mapped if m.get('type') == 'skill_cast']

    assert len(skills) == 0
    assert any(a.get('attacker_name') for a in attacks), f"Missing attacker_name in attacks: {attacks}"
    assert any(a.get('target_name') for a in attacks), f"Missing target_name in attacks: {attacks}"


def test_bonus_attack_maps_names_and_no_skill_cast():
    caster = make_unit('h1', 'Healer', hp=70, max_hp=100, max_mana=100)
    enemy = make_unit('e1', 'Dummy', hp=300)
    caster.mana = 100

    mapped = _mapped_events_from_sim([caster], [enemy])

    attacks = [m for m in mapped if m.get('type') == 'unit_attack']
    skills = [m for m in mapped if m.get('type') == 'skill_cast']

    assert len(skills) == 0
    assert len(attacks) >= 2
    assert all(a.get('attacker_name') for a in attacks)
    assert all(a.get('target_name') for a in attacks)


def test_death_payloads_include_names_without_skills():
    caster = make_unit('d1', 'DoTer', hp=200, max_mana=100)
    target = make_unit('t1', 'Tank', hp=40)
    caster.attack = 100
    caster.mana = 0

    mapped = _mapped_events_from_sim([caster], [target])

    attacks = [m for m in mapped if m.get('type') == 'unit_attack']
    deaths = [m for m in mapped if m.get('type') == 'unit_died']

    assert attacks and all(a.get('attacker_name') for a in attacks) and all(a.get('target_name') for a in attacks)
    assert deaths and all(d.get('unit_name') for d in deaths)


def test_animation_outcome_validator_fails_closed_on_missing_result():
    with pytest.raises(CombatExecutionError, match=r'player->opponent'):
        _validate_attack_animation_outcomes([
            ('animation_start', {
                'attacker_id': 'player',
                'target_id': 'opponent',
                'seq': 12,
            }),
        ])


def test_same_timestamp_lethal_attacks_have_one_canonical_outcome_each():
    player = make_unit('player', 'Player', hp=100)
    opponent = make_unit('opponent', 'Opponent', hp=100)
    player.attack = 200
    opponent.attack = 200

    result = run_combat_simulation(
        [player],
        [opponent],
        skip_per_round_buffs=True,
        skip_per_second_buffs=True,
    )
    events = result['events']

    animations = [
        payload for event_type, payload in events
        if event_type == 'animation_start'
        and payload.get('attacker_id')
        and payload.get('target_id')
    ]
    outcomes = [
        (event_type, payload)
        for event_type, payload in events
        if event_type in {'unit_attack', 'damage', 'damage_dodged'}
    ]

    assert {(a['attacker_id'], a['target_id']) for a in animations} == {
        ('player', 'opponent'),
        ('opponent', 'player'),
    }
    matched = {
        (payload.get('attacker_id'), payload.get('target_id') or payload.get('unit_id')):
        (event_type, payload)
        for event_type, payload in outcomes
        if payload.get('attacker_id')
    }
    assert set(matched) >= {
        ('player', 'opponent'),
        ('opponent', 'player'),
    }

    cancelled_type, cancelled = matched[('opponent', 'player')]
    assert cancelled_type == 'damage_dodged'
    assert cancelled['cause'] == 'attacker_dead_before_impact'
    assert cancelled['damage'] == 0
    assert cancelled['post_hp'] == 100

    mapped = [
        gc.map_event_to_sse_payload(event_type, payload)
        for event_type, payload in events
        if event_type == 'damage_dodged'
    ]
    assert mapped and mapped[0]['cause'] == 'attacker_dead_before_impact'
