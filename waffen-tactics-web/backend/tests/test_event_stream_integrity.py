"""
Tests to ensure mapped SSE payloads include human-readable names
and required fields so the UI doesn't display `null` in messages.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.combat_service import run_combat_simulation
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
