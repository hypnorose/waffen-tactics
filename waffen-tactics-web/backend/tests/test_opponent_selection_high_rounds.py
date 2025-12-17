import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from waffen_tactics.models.player_state import PlayerState
from services.combat_service import prepare_opponent_units_for_combat


class TestHighRoundOpponentSelection(unittest.TestCase):
    def setUp(self):
        # Prepare a mock player state used across tests
        self.mock_player = MagicMock(spec=PlayerState)
        self.mock_player.user_id = 9999
        self.mock_player.wins = 120
        self.mock_player.losses = 0
        self.mock_player.board = []

        # Minimal mock unit used by game_manager
        self.mock_unit = MagicMock()
        self.mock_unit.id = 'unit_001'
        self.mock_unit.name = 'Test Unit'
        self.mock_unit.cost = 1
        self.mock_unit.factions = []
        self.mock_unit.classes = []
        self.mock_unit.stats = MagicMock()
        self.mock_unit.stats.hp = 100
        self.mock_unit.stats.attack = 20
        self.mock_unit.stats.defense = 5
        self.mock_unit.stats.attack_speed = 0.8
        self.mock_unit.stats.max_mana = 100

    @patch('services.combat_service.game_manager')
    @patch('services.combat_service.db_manager')
    def test_system_opponent_selected_at_round_120(self, mock_db_manager, mock_game_manager):
        """If no real player is available, a system bot should be selected for round 120."""
        # Setup mocks: no real player opponent
        mock_db_manager.get_random_opponent = AsyncMock(return_value=None)

        # System opponent data
        opponent_data = {
            'user_id': 2,
            'nickname': 'SystemBot120',
            'wins': 0,
            'level': 1,
            'board': [{'unit_id': 'unit_001', 'star_level': 1}]
        }
        mock_db_manager.get_random_system_opponent = AsyncMock(return_value=opponent_data)

        # Setup game_manager units and synergy engine
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.synergy_engine.compute.return_value = {}
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8}
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8}
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(self.mock_player)

        # Assert
        self.assertEqual(opponent_info['name'], 'SystemBot120')
        self.assertEqual(len(opponent_units), 1)
        self.assertEqual(len(opponent_unit_info), 1)

    @patch('services.combat_service.game_manager')
    @patch('services.combat_service.db_manager')
    def test_system_opponent_selected_at_round_200(self, mock_db_manager, mock_game_manager):
        """System bot should also be selected for round 200 if available."""
        # Set player's rounds to 200
        self.mock_player.wins = 200
        self.mock_player.losses = 0

        mock_db_manager.get_random_opponent = AsyncMock(return_value=None)
        opponent_data = {
            'user_id': 3,
            'nickname': 'SystemBot200',
            'wins': 0,
            'level': 1,
            'board': [{'unit_id': 'unit_001', 'star_level': 1}]
        }
        mock_db_manager.get_random_system_opponent = AsyncMock(return_value=opponent_data)

        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.synergy_engine.compute.return_value = {}
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8}
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8}
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(self.mock_player)

        self.assertEqual(opponent_info['name'], 'SystemBot200')
        self.assertEqual(len(opponent_units), 1)

    @patch('services.combat_service.db_manager')
    def test_no_opponent_raises_runtime_for_high_round(self, mock_db_manager):
        """If neither real nor system opponent exists, the function should raise RuntimeError."""
        mock_db_manager.get_random_opponent = AsyncMock(return_value=None)
        mock_db_manager.get_random_system_opponent = AsyncMock(return_value=None)

        with self.assertRaises(RuntimeError):
            prepare_opponent_units_for_combat(self.mock_player)


if __name__ == '__main__':
    unittest.main()
