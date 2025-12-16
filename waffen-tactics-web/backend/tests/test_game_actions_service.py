"""
Tests for Game Actions Service
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from waffen_tactics.models.player_state import PlayerState
from services.game_actions_service import (
    buy_unit_action, sell_unit_action, move_to_board_action, switch_line_action,
    move_to_bench_action, reroll_shop_action, buy_xp_action, toggle_shop_lock_action
)


class TestGameActionsService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "123"
        self.unit_id = "unit_001"
        self.instance_id = "inst_001"
        self.position = "front"

        # Create mock player
        self.mock_player = MagicMock(spec=PlayerState)
        self.mock_player.user_id = int(self.user_id)
        self.mock_player.to_dict.return_value = {"user_id": self.user_id}

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_buy_unit_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful unit purchase"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.buy_unit.return_value = (True, "Unit purchased successfully")

        # Execute
        success, message, player = buy_unit_action(self.user_id, self.unit_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Unit purchased successfully")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.buy_unit.assert_called_once_with(self.mock_player, self.unit_id)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_buy_unit_action_no_player(self, mock_game_manager, mock_db_manager):
        """Test unit purchase when no player found"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=None)

        # Execute
        success, message, player = buy_unit_action(self.user_id, self.unit_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "No game found")
        self.assertIsNone(player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.buy_unit.assert_not_called()
        mock_db_manager.save_player.assert_not_called()

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_buy_unit_action_buy_failed(self, mock_game_manager, mock_db_manager):
        """Test unit purchase when buy operation fails"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_game_manager.buy_unit.return_value = (False, "Not enough gold")

        # Execute
        success, message, player = buy_unit_action(self.user_id, self.unit_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "Not enough gold")
        self.assertIsNone(player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.buy_unit.assert_called_once_with(self.mock_player, self.unit_id)
        mock_db_manager.save_player.assert_not_called()

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_sell_unit_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful unit sale"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.sell_unit.return_value = (True, "Unit sold successfully")

        # Execute
        success, message, player = sell_unit_action(self.user_id, self.instance_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Unit sold successfully")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.sell_unit.assert_called_once_with(self.mock_player, self.instance_id)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_move_to_board_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful move to board"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.move_to_board.return_value = (True, "Unit moved to board")

        # Execute
        success, message, player = move_to_board_action(self.user_id, self.instance_id, self.position)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Unit moved to board")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.move_to_board.assert_called_once_with(self.mock_player, self.instance_id, self.position)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_switch_line_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful line switch"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.switch_line.return_value = (True, "Unit switched lines")

        # Execute
        success, message, player = switch_line_action(self.user_id, self.instance_id, self.position)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Unit switched lines")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.switch_line.assert_called_once_with(self.mock_player, self.instance_id, self.position)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_move_to_bench_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful move to bench"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.move_to_bench.return_value = (True, "Unit moved to bench")

        # Execute
        success, message, player = move_to_bench_action(self.user_id, self.instance_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Unit moved to bench")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.move_to_bench.assert_called_once_with(self.mock_player, self.instance_id)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_reroll_shop_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful shop reroll"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.reroll_shop.return_value = (True, "Shop rerolled")

        # Execute
        success, message, player = reroll_shop_action(self.user_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Shop rerolled")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.reroll_shop.assert_called_once_with(self.mock_player)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    @patch('services.game_actions_service.game_manager')
    def test_buy_xp_action_success(self, mock_game_manager, mock_db_manager):
        """Test successful XP purchase"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()
        mock_game_manager.buy_xp.return_value = (True, "XP purchased")

        # Execute
        success, message, player = buy_xp_action(self.user_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "XP purchased")
        self.assertEqual(player, self.mock_player)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_game_manager.buy_xp.assert_called_once_with(self.mock_player)
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    def test_toggle_shop_lock_action_success(self, mock_db_manager):
        """Test successful shop lock toggle"""
        # Setup mocks
        self.mock_player.locked_shop = False
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()

        # Execute
        success, message, player = toggle_shop_lock_action(self.user_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Sklep zablokowany!")
        self.assertEqual(player, self.mock_player)
        self.assertTrue(player.locked_shop)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)

    @patch('services.game_actions_service.db_manager')
    def test_toggle_shop_lock_action_unlock(self, mock_db_manager):
        """Test successful shop unlock toggle"""
        # Setup mocks
        self.mock_player.locked_shop = True
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        mock_db_manager.save_player = AsyncMock()

        # Execute
        success, message, player = toggle_shop_lock_action(self.user_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Sklep odblokowany!")
        self.assertEqual(player, self.mock_player)
        self.assertFalse(player.locked_shop)
        mock_db_manager.load_player.assert_called_once_with(int(self.user_id))
        mock_db_manager.save_player.assert_called_once_with(self.mock_player)


if __name__ == '__main__':
    unittest.main()