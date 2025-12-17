import time
import pytest

from waffen_tactics.services.combat_simulator import CombatSimulator
from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats
from waffen_tactics.services.skill_parser import skill_parser


def make_unit(unit_id: str, name: str, hp: int = 100, skill_data: dict = None):
    # Create Stats object expected by CombatSimulator
    # Give casters a low max_mana so they cast quickly during simulation
    if skill_data:
        stats = Stats(attack=20, hp=hp, defense=5, max_mana=10, attack_speed=1.0, mana_on_attack=10, mana_regen=0)
        max_mana = 10
    else:
        stats = Stats(attack=15, hp=hp, defense=5, max_mana=100, attack_speed=1.0, mana_on_attack=0, mana_regen=0)
        max_mana = 100
    u = CombatUnit(id=unit_id, name=name, hp=hp, attack=20, defense=5, attack_speed=1.0, stats=stats, max_mana=max_mana)
    if skill_data:
        parsed = skill_parser._parse_skill(skill_data)
        # Attach skill in legacy place if tests expect 'skill' dict
        u.skill = {'effect': {'skill': parsed}}  # skill_executor looks for this
    return u


def collect_events_for_combat(team_a, team_b, duration_seconds=5.0):
    events = []

    def callback(ev_type, data):
        events.append((ev_type, data))

    sim = CombatSimulator()
    sim.simulate(team_a, team_b, event_callback=callback)
    return events


def test_delay_wrapped_dot_generates_delayed_events():
    # Create caster with a delay that then applies DoT
    skill = {
        'name': 'Delayed Burn',
        'description': 'Wait then apply DoT',
        'mana_cost': 0,
        'effects': [
            {'type': 'delay', 'duration': 1.5},
            {'type': 'damage_over_time', 'target': 'single_enemy', 'damage': 10, 'duration': 4, 'interval': 1}
        ]
    }

    caster = make_unit('caster_1', 'Caster', hp=200, skill_data=skill)
    target = make_unit('target_1', 'Target', hp=200)

    events = collect_events_for_combat([caster], [target], duration_seconds=6.0)

    # Find a damage_over_time_applied event and its timestamp
    dot_applied = [e for e in events if e[0] == 'damage_over_time_applied']
    assert len(dot_applied) >= 1, f"Expected at least one DoT applied event, got: {dot_applied}"

    applied_evt = dot_applied[0][1]
    assert applied_evt.get('unit_id') == target.id
    assert 'timestamp' in applied_evt
    applied_ts = applied_evt['timestamp']

    # There should be at least one damage_over_time_tick after the applied timestamp
    ticks = [e for e in events if e[0] == 'damage_over_time_tick' and e[1].get('timestamp', 0) > applied_ts]
    assert len(ticks) >= 1, f"Expected at least one DoT tick after application; events: {events}"


def test_delay_with_delayed_damage_event_timestamps_reflect_delay():
    # A skill that delays for 2s then does immediate damage
    skill = {
        'name': 'Delayed Strike',
        'description': 'Delay then strike',
        'mana_cost': 0,
        'effects': [
            {'type': 'delay', 'duration': 2.0},
            {'type': 'damage', 'target': 'single_enemy', 'amount': 50}
        ]
    }

    caster = make_unit('caster_2', 'Striker', hp=200, skill_data=skill)
    target = make_unit('target_2', 'Dummy', hp=200)

    events = collect_events_for_combat([caster], [target], duration_seconds=4.0)

    # Find unit_attack events caused by skill (is_skill can be True in some flows)
    attacks = [e for e in events if e[0] in ('unit_attack',) and e[1].get('attacker_id') == caster.id]
    # Also consider unit_attack generated from old path may use attacker_name matching
    assert len(attacks) >= 1, f"Expected attack events, got: {events}"

    # Ensure the first attack event timestamp is >= delay (i.e., ~2s)
    first_ts = min(e[1].get('timestamp', 0) for e in attacks)
    assert first_ts >= 1.9, f"Expected attack after ~2s delay, got timestamp {first_ts}"
