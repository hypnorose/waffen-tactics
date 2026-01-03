import copy
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.unit import Unit, Stats, Skill
from waffen_tactics.models.player_state import PlayerState


def make_stats():
    return Stats(attack=10, hp=100, defense=5, max_mana=100, attack_speed=1.0)


def make_skill():
    return Skill(name='', description='')


def test_xn_yakuza_applies_only_to_self():
    # Trait definition (matching attachment): target at trait level = 'self'
    traits = [
        {
            'name': 'XN Yakuza',
            'type': 'class',
            'target': 'self',
            'thresholds': [1],
            'modular_effects': [
                [
                    {
                        'trigger': 'on_win',
                        'conditions': {},
                        'rewards': [
                            {
                                'type': 'dynamic_scaling',
                                'atk_per_win': 1,
                                'def_per_win': 1,
                                'hp_percent_per_win': 1,
                                'as_per_win': 0.01
                            }
                        ]
                    }
                ]
            ]
        }
    ]

    engine = SynergyEngine(traits)

    stats = make_stats()
    skill = make_skill()
    unit_with = Unit(id='u_with', name='With', cost=1, factions=[], classes=['XN Yakuza'], stats=stats, skill=skill)
    unit_without = Unit(id='u_without', name='Without', cost=1, factions=[], classes=[], stats=copy.deepcopy(stats), skill=skill)

    active = engine.compute([unit_with, unit_without])
    assert 'XN Yakuza' in active

    base_stats = {'hp': 100, 'attack': 10, 'defense': 5, 'attack_speed': 1.0}
    player = PlayerState(user_id=1, username='p')
    # Simulate 2 wins so atk_per_win should add +2 attack
    player.wins = 2

    new_with = engine.apply_dynamic_effects(unit_with, copy.deepcopy(base_stats), active, player)
    new_without = engine.apply_dynamic_effects(unit_without, copy.deepcopy(base_stats), active, player)

    # Expected: unit_with attack increased by atk_per_win * wins = 2
    assert new_with['attack'] == base_stats['attack'] + 2
    # unit_without should NOT receive the dynamic scaling because trait target is 'self'
    assert new_without['attack'] == base_stats['attack']


def test_trait_target_level_default_used_for_stat_buffs():
    # Trait-level target 'self' with a per-tier stat_buff effect that does not specify 'target'
    traits = [
        {
            'name': 'XN Test',
            'type': 'class',
            'target': 'self',
            'thresholds': [1],
            'modular_effects': [
                [
                    {
                        'trigger': 'per_round',
                        'conditions': {},
                        'rewards': [
                            {
                                'type': 'stat_buff',
                                'stat': 'attack',
                                'value': 5
                            }
                        ]
                    }
                ]
            ]
        }
    ]

    engine = SynergyEngine(traits)

    stats = make_stats()
    skill = make_skill()
    unit_with = Unit(id='u_with2', name='With2', cost=1, factions=[], classes=['XN Test'], stats=stats, skill=skill)
    unit_without = Unit(id='u_without2', name='Without2', cost=1, factions=[], classes=[], stats=copy.deepcopy(stats), skill=skill)

    active = engine.compute([unit_with, unit_without])
    assert 'XN Test' in active

    base_stats = {'hp': 100, 'attack': 10, 'defense': 5, 'attack_speed': 1.0}
    # apply_stat_buffs is used to apply flat stat buffs
    buffed_with = engine.apply_stat_buffs(base_stats.copy(), unit_with, active)
    buffed_without = engine.apply_stat_buffs(base_stats.copy(), unit_without, active)

    # Unit with trait should get +5 attack
    assert buffed_with['attack'] == 15
    # Unit without trait should remain unchanged
    assert buffed_without['attack'] == 10
