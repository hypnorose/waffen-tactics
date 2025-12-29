import copy

from waffen_tactics.services.synergy import SynergyEngine


class DummyUnit:
    def __init__(self):
        self.id = 'u1'
        self.factions = []
        self.classes = []


def test_apply_dynamic_effects_with_player_none_does_not_raise_and_uses_zero_wins():
    # Trait that gives +1 attack per win
    traits = [
        {
            'name': 'TestTrait',
            'tier': 1,
            'modular_effects': [
                [
                    {'rewards': [{'type': 'dynamic_scaling', 'atk_per_win': 1}]}
                ]
            ]
        }
    ]

    engine = SynergyEngine(traits)
    unit = DummyUnit()
    base_stats = {'hp': 100, 'attack': 10, 'defense': 5, 'attack_speed': 1.0}
    active = {'TestTrait': (1, 1)}

    # player is None (opponent case). Should not raise and attack should remain unchanged
    out = engine.apply_dynamic_effects(unit, copy.deepcopy(base_stats), active, None)
    assert out['attack'] == 10
    assert out['hp'] == 100