import json
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.unit import Unit, Stats, Skill
from waffen_tactics.models.player_state import PlayerState


def make_unit(uid, name, factions=None, classes=None):
    stats = Stats(attack=50, hp=500, defense=10, max_mana=100, attack_speed=1.0)
    skill = Skill(name="s", description="d", mana_cost=100, effect={})
    return Unit(id=uid, name=name, cost=1, factions=factions or [], classes=classes or [], stats=stats, skill=skill)


def test_win_scaling_trait_applies_correctly():
    # Provide an inline trait definition instead of loading from external JSON
    traits = [
        {
            'name': 'XN Yakuza',
            'type': 'faction',
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

    # Create a unit that has the trait
    u = make_unit('u1', 'Yakuza', factions=['XN Yakuza'])

    # Compute active synergies for a single unit -> threshold 1 should activate tier 1
    active = engine.compute([u])
    assert 'XN Yakuza' in active

    # Player with 3 wins
    player = PlayerState(user_id=1)
    player.wins = 3

    base_stats = {'hp': 500, 'attack': 50, 'defense': 10, 'attack_speed': 1.0}
    new_stats = engine.apply_dynamic_effects(u, base_stats, active, player)

    # From traits.json: atk_per_win=1, def_per_win=1, hp_percent_per_win=1, as_per_win=0.01
    assert new_stats['attack'] == 50 + 1 * 3
    assert new_stats['defense'] == 10 + 1 * 3
    # HP should be increased by 1% per win: 500 * (1 + 3/100) = 515
    assert new_stats['hp'] == int(500 * (1 + (1 * 3) / 100.0))
    # attack speed should be increased by 0.01 per win
    assert abs(new_stats['attack_speed'] - (1.0 + 0.01 * 3)) < 1e-6
