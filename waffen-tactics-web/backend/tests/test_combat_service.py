"""
Tests for Combat Service
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from waffen_tactics.models.player_state import PlayerState
from waffen_tactics.services.combat_shared import CombatUnit
from services.combat_service import (
    prepare_player_units_for_combat, prepare_opponent_units_for_combat,
    run_combat_simulation, process_combat_results
)


class TestCombatService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "123"

        # Create mock player
        self.mock_player = MagicMock(spec=PlayerState)
        self.mock_player.user_id = int(self.user_id)
        self.mock_player.hp = 100
        self.mock_player.board = []
        self.mock_player.max_board_size = 7
        self.mock_player.wins = 5
        self.mock_player.losses = 3
        self.mock_player.level = 1  # Set as int
        self.mock_player.xp = 0  # Set as int
        self.mock_player.gold = 10  # Set as int
        self.mock_player.streak = 0  # Set as int
        self.mock_player.round_number = 1  # Set as int
        self.mock_player.locked_shop = False
        self.mock_player.xp_to_next_level = 2  # Mock the property
        self.mock_player.add_xp = MagicMock(side_effect=lambda amount: (setattr(self.mock_player, 'xp', getattr(self.mock_player, 'xp', 0) + amount), None)[-1])  # Mock add_xp to actually add XP
        self.mock_player.to_dict.return_value = {"user_id": self.user_id}

        # Create mock unit
        self.mock_unit = MagicMock()
        self.mock_unit.id = "unit_001"
        self.mock_unit.name = "Test Unit"
        self.mock_unit.cost = 1
        self.mock_unit.factions = ["TestFaction"]
        self.mock_unit.classes = ["TestClass"]
        self.mock_unit.stats = MagicMock()
        self.mock_unit.stats.hp = 100
        self.mock_unit.stats.attack = 20
        self.mock_unit.stats.defense = 5
        self.mock_unit.stats.attack_speed = 0.8
        self.mock_unit.stats.max_mana = 100
        self.mock_unit.stats.mana_regen = 5

        # Create mock unit instance
        self.mock_unit_instance = MagicMock()
        self.mock_unit_instance.unit_id = "unit_001"
        self.mock_unit_instance.instance_id = "inst_001"
        self.mock_unit_instance.star_level = 1
        self.mock_unit_instance.position = "front"
        self.mock_unit_instance.persistent_buffs = {}

    @patch('services.combat_service.db_manager')
    @patch('services.combat_service.game_manager')
    def test_prepare_player_units_for_combat_success(self, mock_game_manager, mock_db_manager):
        """Test successful player unit preparation"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        self.mock_player.board = [self.mock_unit_instance]
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.get_board_synergies.return_value = {"TestTrait": (1, 1)}
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8, 'max_mana': 100, 'current_mana': 0
        }
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Player units prepared")
        self.assertIsNotNone(result)
        player_units, player_unit_info, synergies_data = result
        self.assertEqual(len(player_units), 1)
        self.assertEqual(len(player_unit_info), 1)
        self.assertIn("TestTrait", synergies_data)

    @patch('services.combat_service.db_manager')
    def test_prepare_player_units_for_combat_no_player(self, mock_db_manager):
        """Test player unit preparation when no player found"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=None)

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "Player not found")
        self.assertIsNone(result)

    @patch('services.combat_service.db_manager')
    def test_prepare_player_units_for_combat_defeated(self, mock_db_manager):
        """Test player unit preparation when player is defeated"""
        # Setup mocks
        self.mock_player.hp = 0
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "Player is defeated and cannot fight")
        self.assertIsNone(result)

    @patch('services.combat_service.db_manager')
    def test_prepare_player_units_for_combat_no_board(self, mock_db_manager):
        """Test player unit preparation when no units on board"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "No units on board")
        self.assertIsNone(result)

    @patch('services.combat_service.db_manager')
    @patch('services.combat_service.game_manager')
    def test_prepare_opponent_units_for_combat_success(self, mock_game_manager, mock_db_manager):
        """Test successful opponent unit preparation"""
        # Setup mocks
        opponent_data = {
            'nickname': 'TestOpponent',
            'wins': 10,
            'level': 5,
            'board': [{'unit_id': 'unit_001', 'star_level': 1}]
        }
        mock_db_manager.get_random_opponent = AsyncMock(return_value=opponent_data)
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.synergy_engine.compute.return_value = {}
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(self.mock_player)

        # Assert
        self.assertEqual(len(opponent_units), 1)
        self.assertEqual(len(opponent_unit_info), 1)
        self.assertEqual(opponent_info['name'], 'TestOpponent')
        self.assertEqual(opponent_info['wins'], 10)
        self.assertEqual(opponent_info['level'], 5)

    @patch('services.combat_service.db_manager')
    def test_prepare_opponent_units_for_combat_fallback(self, mock_db_manager):
        """Test opponent unit preparation fallback when no opponent found"""
        # Setup mocks
        mock_db_manager.get_random_opponent = AsyncMock(return_value=None)

        # Execute & Assert: no DB opponent should cause an error (no ad-hoc fallbacks)
        with self.assertRaises(RuntimeError):
            prepare_opponent_units_for_combat(self.mock_player)

    @patch('services.combat_service.CombatSimulator')
    def test_run_combat_simulation_success(self, mock_simulator_class):
        """Test successful combat simulation"""
        # Setup mocks
        mock_simulator = MagicMock()
        mock_simulator.simulate.return_value = {
            'winner': 'team_a',
            'duration': 10.5,
            'survivors': {'team_a': ['unit1'], 'team_b': []},
            'log': ['Combat started', 'Unit died']
        }
        mock_simulator_class.return_value = mock_simulator

        player_units = [MagicMock(spec=CombatUnit)]
        opponent_units = [MagicMock(spec=CombatUnit)]

        # Execute
        result = run_combat_simulation(player_units, opponent_units)

        # Assert
        self.assertEqual(result['winner'], 'team_a')
        self.assertEqual(result['duration'], 10.5)
        self.assertIn('events', result)
        mock_simulator.simulate.assert_called_once()

    @patch('services.combat_service.CombatSimulator')
    def test_run_combat_simulation_error(self, mock_simulator_class):
        """Test combat simulation error handling"""
        # Setup mocks
        mock_simulator_class.side_effect = Exception("Simulation failed")

        player_units = [MagicMock(spec=CombatUnit)]
        opponent_units = [MagicMock(spec=CombatUnit)]

        # Execute
        result = run_combat_simulation(player_units, opponent_units)

        # Assert
        self.assertEqual(result['winner'], 'error')
        self.assertEqual(result['duration'], 0)
        self.assertIn('Combat error', result['log'][0])

    @patch('services.combat_service.game_manager')
    def test_process_combat_results_victory(self, mock_game_manager):
        """Test processing combat results for victory"""
        # Setup mocks
        self.mock_player.streak = 0
        self.mock_player.board = []
        self.mock_player.locked_shop = False

        mock_game_manager.get_board_synergies.return_value = {}
        mock_game_manager.generate_shop = MagicMock()

        result = {'winner': 'team_a'}
        collected_stats_maps = {}

        # Execute
        game_over, result_data = process_combat_results(self.mock_player, result, collected_stats_maps)

        # Assert
        self.assertFalse(game_over)
        self.assertEqual(result_data['result_message'], "🎉 ZWYCIĘSTWO!")
        self.assertEqual(self.mock_player.wins, 6)  # Increased by 1
        self.assertEqual(self.mock_player.streak, 1)  # Increased by 1
        self.mock_player.add_xp.assert_called_once_with(2)
        self.assertIn('gold_breakdown', result_data)

    @patch('services.combat_service.game_manager')
    def test_process_combat_results_defeat(self, mock_game_manager):
        """Test processing combat results for defeat"""
        # Setup mocks
        self.mock_player.hp = 100
        self.mock_player.streak = 5
        self.mock_player.board = []
        self.mock_player.locked_shop = False

        mock_game_manager.get_board_synergies.return_value = {}
        mock_game_manager.generate_shop = MagicMock()

        result = {'winner': 'team_b', 'surviving_star_sum': 5}
        collected_stats_maps = {}

        # Execute
        game_over, result_data = process_combat_results(self.mock_player, result, collected_stats_maps)

        # Assert
        self.assertFalse(game_over)
        self.assertIn('PRZEGRANA', result_data['result_message'])
        self.assertEqual(self.mock_player.hp, 90)  # Lost 10 HP (5 * 2)
        self.assertEqual(self.mock_player.streak, 0)  # Reset to 0

    @patch('services.combat_service.game_manager')
    def test_process_combat_results_game_over(self, mock_game_manager):
        """Test processing combat results for game over"""
        # Setup mocks
        self.mock_player.hp = 5  # Low HP
        self.mock_player.streak = 5
        self.mock_player.board = []
        self.mock_player.locked_shop = False

        mock_game_manager.get_board_synergies.return_value = {}
        mock_game_manager.generate_shop = MagicMock()

        result = {'winner': 'team_b', 'surviving_star_sum': 5}  # Will cause 10 HP loss
        collected_stats_maps = {}

        # Execute
        game_over, result_data = process_combat_results(self.mock_player, result, collected_stats_maps)

        # Assert
        self.assertTrue(game_over)
        self.assertIn('Koniec gry', result_data['result_message'])
        self.assertEqual(self.mock_player.hp, -5)  # Went below 0


if __name__ == '__main__':
    unittest.main()