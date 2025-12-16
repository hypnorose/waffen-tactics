"""
Tests for Game Management Service - Pure business logic functions
"""
import unittest
from unittest.mock import Mock, patch, AsyncMock
from services.game_management_service import (
    get_player_state_data,
    create_new_game_data,
    reset_player_game_data,
    surrender_player_game_data
)


class TestGameManagementService(unittest.TestCase):
    """Test cases for game management business logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "123"
        self.username = "TestPlayer"

        # Mock player object
        self.mock_player = Mock()
        self.mock_player.user_id = 123
        self.mock_player.level = 5
        self.mock_player.gold = 100
        self.mock_player.wins = 3
        self.mock_player.losses = 1
        self.mock_player.round_number = 7
        self.mock_player.last_shop = ['unit1', 'unit2']
        self.mock_player.board = [
            Mock(unit_id='board_unit1', star_level=2),
            Mock(unit_id='board_unit2', star_level=1)
        ]

    @patch('services.game_management_service.db_manager')
    def test_get_player_state_data_existing_player(self, mock_db_manager):
        """Test getting state data for existing player"""
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)

        result = get_player_state_data(self.user_id)

        self.assertIsNotNone(result)
        self.assertEqual(result['user_id'], 123)
        self.assertEqual(result['level'], 5)
        self.assertEqual(result['gold'], 100)
        self.assertEqual(result['wins'], 3)
        self.assertEqual(result['losses'], 1)
        self.assertEqual(result['round_number'], 7)
        self.assertEqual(result['last_shop'], ['unit1', 'unit2'])
        self.assertEqual(result['shop'], ['unit1', 'unit2'])
        self.assertFalse(result['needs_start'])
        self.assertEqual(len(result['board']), 2)

    @patch('services.game_management_service.db_manager')
    def test_get_player_state_data_no_player(self, mock_db_manager):
        """Test getting state data when no player exists"""
        mock_db_manager.load_player = AsyncMock(return_value=None)

        result = get_player_state_data(self.user_id)

        self.assertIsNone(result)

    @patch('services.game_management_service.db_manager')
    @patch('services.game_management_service.game_manager')
    def test_create_new_game_data_new_player(self, mock_game_manager, mock_db_manager):
        """Test creating new game for new player"""
        mock_db_manager.load_player = AsyncMock(return_value=None)
        mock_game_manager.create_new_player.return_value = self.mock_player
        mock_db_manager.save_player = AsyncMock()

        with patch('services.game_management_service.get_player_state_data') as mock_get_state:
            mock_get_state.return_value = {'user_id': 123, 'level': 1}

            result = create_new_game_data(self.user_id)

            mock_game_manager.create_new_player.assert_called_once_with(123)
            mock_game_manager.generate_shop.assert_called_once_with(self.mock_player)
            self.assertEqual(result, {'user_id': 123, 'level': 1})

    @patch('services.game_management_service.db_manager')
    def test_reset_player_game_data_no_player(self, mock_db_manager):
        """Test resetting when no player exists"""
        mock_db_manager.load_player = AsyncMock(return_value=None)

        with self.assertRaises(ValueError) as context:
            reset_player_game_data(self.user_id)

        self.assertEqual(str(context.exception), "No game found")

    @patch('services.game_management_service.db_manager')
    def test_surrender_player_game_data_no_player(self, mock_db_manager):
        """Test surrendering when no player exists"""
        mock_db_manager.load_player = AsyncMock(return_value=None)

        with self.assertRaises(ValueError) as context:
            surrender_player_game_data(self.user_id, self.username)

        self.assertEqual(str(context.exception), "No game found")


if __name__ == '__main__':
    unittest.main()