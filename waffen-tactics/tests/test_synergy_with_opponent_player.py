from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.player_state import PlayerState


class DummyUnit:
    def __init__(self):
        self.id = 'u1'
        self.factions = []
        self.classes = []

    def _set_hp(self, value, caller_module=None):
        try:
            self.hp = int(value)
        except Exception:
            self.hp = value


def test_dynamic_scaling_uses_player_wins_when_provided():
    # Trait that gives +2 attack per win
    traits = [
        {
            'name': 'WinTrait',
            'tier': 1,
            'modular_effects': [
                [
                    {'rewards': [{'type': 'dynamic_scaling', 'atk_per_win': 2}]}
                ]
            ]
        }
    ]

    engine = SynergyEngine(traits)
    unit = DummyUnit()
    base_stats = {'hp': 100, 'attack': 10, 'defense': 5, 'attack_speed': 1.0}
    active = {'WinTrait': (1, 1)}

    # Create a PlayerState with wins=3
    p = PlayerState(user_id=123, username='bot', wins=3, losses=0)
    out = engine.apply_dynamic_effects(unit, base_stats.copy(), active, p)
    # attack should have increased by 2 * wins = 6
    assert out['attack'] == 16
