from waffen_tactics.services.combat_unit import CombatUnit
from waffen_tactics.models.unit import Stats
from waffen_tactics.models.skill import Skill, Effect, EffectType, TargetType


def make_unit(unit_id: str, name: str, hp: int = 100, skill_data: dict = None, attack_speed: float = 1.0, max_mana: int = 100, max_hp: int = None):
    if max_hp is None:
        max_hp = hp
    stats = Stats(attack=20, hp=max_hp, defense=5, max_mana=max_mana, attack_speed=attack_speed, mana_on_attack=0, mana_regen=0)
    u = CombatUnit(id=unit_id, name=name, hp=hp, attack=20, defense=5, attack_speed=attack_speed, stats=stats, max_mana=max_mana)
    if skill_data:
        # Hardcoded skill instead of parsing
        u.skill = {'effect': {'skill': Skill(
            name=skill_data['name'],
            description=skill_data['description'],
            mana_cost=skill_data['mana_cost'],
            effects=[Effect(
                type=EffectType(skill_data['effects'][0]['type']),
                target=TargetType(skill_data['effects'][0]['target']),
                params=skill_data['effects'][0]
            )]
        )}}
    return u


def collect_events(team_a, team_b, max_time=3.0):
    events = []
    def cb(t, d):
        events.append((t, d))
    from waffen_tactics.services.combat_simulator import CombatSimulator
    sim = CombatSimulator()
    sim.simulate(team_a, team_b, event_callback=cb)
    return events


def test_heal_skill_is_ignored_and_basic_attacks_continue():
    # Skills are disabled in the current ruleset, so this setup should
    # behave like a normal attacker with no heal side effects.
    skill = {
        'name': 'Group Heal',
        'description': 'Heal allies',
        'mana_cost': 0,
        'effects': [
            {'type': 'heal', 'target': 'ally_team', 'amount': 40}
        ]
    }

    caster = make_unit('caster_h', 'Healer', hp=150, skill_data=skill, attack_speed=20.0, max_mana=10, max_hp=150)
    ally = make_unit('ally_1', 'Ally', hp=80, attack_speed=1.0, max_hp=100)
    enemy = make_unit('enemy_1', 'Enemy', hp=200, attack_speed=5.0, max_hp=200)

    # Ensure caster has full mana so skill can be cast quickly
    caster.mana = caster.max_mana

    events = collect_events([caster, ally], [enemy], max_time=3.0)

    heal_events = [e for e in events if e[0] == 'unit_heal']
    skill_events = [e for e in events if e[0] == 'skill_cast']
    attack_events = [e for e in events if e[0] == 'unit_attack' and e[1].get('attacker_id') == 'caster_h']

    assert len(skill_events) == 0
    assert len(heal_events) == 0
    assert len(attack_events) >= 1
    assert all(not e[1].get('is_skill', False) for e in attack_events)
