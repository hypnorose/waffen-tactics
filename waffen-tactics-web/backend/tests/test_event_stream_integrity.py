"""
Tests to ensure mapped SSE payloads include human-readable names
and required fields so the UI doesn't display `null` in messages.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.combat_service import run_combat_simulation
from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType
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


def test_attack_and_skill_mapped_have_names():
    dmg = Effect(type=EffectType.DAMAGE, target=TargetType.SINGLE_ENEMY, params={'amount': 40})
    stun = Effect(type=EffectType.STUN, target=TargetType.SINGLE_ENEMY, params={'duration': 1.5})
    skill = Skill(name='System Hack', description='Damage+Stun', mana_cost=50, effects=[dmg, stun])

    caster = make_unit('u1', 'Piwniczak', hp=200, max_mana=150, skill=skill)
    target = make_unit('u2', 'V7', hp=200)
    caster.mana = 150

    mapped = _mapped_events_from_sim([caster], [target])

    # Ensure at least one skill_cast and at least one unit_attack have names
    attacks = [m for m in mapped if m.get('type') == 'unit_attack']
    skills = [m for m in mapped if m.get('type') == 'skill_cast']
    stuns = [m for m in mapped if m.get('type') == 'unit_stunned']

    assert len(skills) >= 1
    assert any(a.get('attacker_name') for a in attacks), f"Missing attacker_name in attacks: {attacks}"
    assert any(a.get('target_name') for a in attacks), f"Missing target_name in attacks: {attacks}"
    assert any(s.get('caster_name') for s in skills), f"Missing caster_name in skills: {skills}"
    # stun events should include unit_name and caster_name
    if stuns:
        assert all(s.get('unit_name') for s in stuns)
        assert all(s.get('caster_name') for s in stuns)


def test_heal_buff_shield_mapped_have_names():
    effects = [
        Effect(type=EffectType.HEAL, target=TargetType.SELF, params={'amount': 30}),
        Effect(type=EffectType.BUFF, target=TargetType.SELF, params={'stat': 'attack', 'value': 5, 'duration': 5}),
        Effect(type=EffectType.SHIELD, target=TargetType.SELF, params={'amount': 20, 'duration': 3})
    ]
    skill = Skill(name='Support Wave', description='Support', mana_cost=50, effects=effects)

    caster = make_unit('h1', 'Healer', hp=70, max_hp=100, max_mana=100, skill=skill)
    enemy = make_unit('e1', 'Dummy', hp=1)
    caster.mana = 100

    mapped = _mapped_events_from_sim([caster], [enemy])

    heals = [m for m in mapped if m.get('type') == 'unit_heal']
    buffs = [m for m in mapped if m.get('type') == 'stat_buff']
    shields = [m for m in mapped if m.get('type') == 'shield_applied']

    assert heals and all(h.get('unit_name') for h in heals)
    assert buffs and all(b.get('unit_name') for b in buffs) and all(b.get('caster_name') for b in buffs)
    assert shields and all(s.get('unit_name') for s in shields) and all(s.get('caster_name') for s in shields)


def test_dot_and_death_include_names():
    eff = Effect(type=EffectType.DAMAGE_OVER_TIME, target=TargetType.SINGLE_ENEMY, params={'damage': 5, 'duration': 2, 'interval': 1.0})
    skill = Skill(name='Corrupting Bolt', description='DoT', mana_cost=50, effects=[eff])

    caster = make_unit('d1', 'DoTer', hp=200, max_mana=100, skill=skill)
    target = make_unit('t1', 'Tank', hp=1000)
    caster.mana = 100

    mapped = _mapped_events_from_sim([caster], [target])

    dot_applied = [m for m in mapped if m.get('type') == 'damage_over_time_applied']
    deaths = [m for m in mapped if m.get('type') == 'unit_died']

    assert dot_applied and all(d.get('unit_name') for d in dot_applied) and all(d.get('caster_name') for d in dot_applied)
    # If a death occurred, ensure it has a name
    if deaths:
        assert all(d.get('unit_name') for d in deaths)
