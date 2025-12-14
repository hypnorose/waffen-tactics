"""
Tests for game_actions.py
"""
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from routes.game_actions import buy_unit, sell_unit, move_to_board, move_to_bench, reroll_shop, buy_xp, toggle_shop_lock


class TestBuyUnit:
    """Test the buy_unit function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_buy_unit_success(self, mock_gm, mock_db):
        """Test successful unit purchase"""
        # Mock request
        with patch('routes.game_actions.request') as mock_request:
            mock_request.json = {'unit_id': 'test_unit'}

            # Mock player
            mock_player = Mock()
            mock_player.gold = 10
            mock_db.load_player.return_value = mock_player

            # Mock game manager buy_unit
            mock_gm.buy_unit.return_value = (True, "Unit bought successfully")

            # Mock enrich_player_state
            with patch('routes.game_actions.enrich_player_state') as mock_enrich:
                mock_enrich.return_value = {'gold': 5, 'message': 'success'}

                result = buy_unit(123)

                assert result.status_code == 200
                data = result.get_json()
                assert 'state' in data
                assert data['state']['gold'] == 5

                mock_db.load_player.assert_called_with(123)
                mock_db.save_player.assert_called_with(mock_player)

    @patch('routes.game_actions.db_manager')
    def test_buy_unit_no_player(self, mock_db):
        """Test buy_unit when player not found"""
        mock_db.load_player.return_value = None

        with patch('routes.game_actions.request'):
            result = buy_unit(123)

            assert result.status_code == 404
            assert result.get_json()['error'] == 'Player not found'

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_buy_unit_buy_failed(self, mock_gm, mock_db):
        """Test buy_unit when purchase fails"""
        with patch('routes.game_actions.request') as mock_request:
            mock_request.json = {'unit_id': 'test_unit'}

            mock_player = Mock()
            mock_db.load_player.return_value = mock_player

            mock_gm.buy_unit.return_value = (False, "Not enough gold")

            result = buy_unit(123)

            assert result.status_code == 400
            assert result.get_json()['error'] == "Not enough gold"


class TestSellUnit:
    """Test the sell_unit function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_sell_unit_success(self, mock_gm, mock_db):
        """Test successful unit sale"""
        with patch('routes.game_actions.request') as mock_request:
            mock_request.json = {'instance_id': 'inst1'}

            mock_player = Mock()
            mock_db.load_player.return_value = mock_player

            mock_gm.sell_unit.return_value = (True, "Unit sold")

            with patch('routes.game_actions.enrich_player_state') as mock_enrich:
                mock_enrich.return_value = {'gold': 15, 'message': 'sold'}

                result = sell_unit(123)

                assert result.status_code == 200
                mock_gm.sell_unit.assert_called_with(mock_player, 'inst1')


class TestMoveToBoard:
    """Test the move_to_board function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_move_to_board_success(self, mock_gm, mock_db):
        """Test successful move to board"""
        with patch('routes.game_actions.request') as mock_request:
            mock_request.json = {'instance_id': 'inst1'}

            mock_player = Mock()
            mock_db.load_player.return_value = mock_player

            mock_gm.move_to_board.return_value = (True, "Moved to board")

            with patch('routes.game_actions.enrich_player_state') as mock_enrich:
                mock_enrich.return_value = {'board': ['unit1']}

                result = move_to_board(123)

                assert result.status_code == 200
                mock_gm.move_to_board.assert_called_with(mock_player, 'inst1')


class TestMoveToBench:
    """Test the move_to_bench function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_move_to_bench_success(self, mock_gm, mock_db):
        """Test successful move to bench"""
        with patch('routes.game_actions.request') as mock_request:
            mock_request.json = {'instance_id': 'inst1'}

            mock_player = Mock()
            mock_db.load_player.return_value = mock_player

            mock_gm.move_to_bench.return_value = (True, "Moved to bench")

            with patch('routes.game_actions.enrich_player_state') as mock_enrich:
                mock_enrich.return_value = {'bench': ['unit1']}

                result = move_to_bench(123)

                assert result.status_code == 200
                mock_gm.move_to_bench.assert_called_with(mock_player, 'inst1')


class TestRerollShop:
    """Test the reroll_shop function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_reroll_shop_success(self, mock_gm, mock_db):
        """Test successful shop reroll"""
        mock_player = Mock()
        mock_db.load_player.return_value = mock_player

        mock_gm.reroll_shop.return_value = (True, "Shop rerolled")

        with patch('routes.game_actions.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'shop': ['new_unit']}

            result = reroll_shop(123)

            assert result.status_code == 200
            mock_gm.reroll_shop.assert_called_with(mock_player)


class TestBuyXp:
    """Test the buy_xp function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_buy_xp_success(self, mock_gm, mock_db):
        """Test successful XP purchase"""
        mock_player = Mock()
        mock_db.load_player.return_value = mock_player

        mock_gm.buy_xp.return_value = (True, "XP bought")

        with patch('routes.game_actions.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'xp': 10, 'level': 2}

            result = buy_xp(123)

            assert result.status_code == 200
            mock_gm.buy_xp.assert_called_with(mock_player)


class TestToggleShopLock:
    """Test the toggle_shop_lock function"""

    @patch('routes.game_actions.db_manager')
    @patch('routes.game_actions.game_manager')
    def test_toggle_shop_lock_success(self, mock_gm, mock_db):
        """Test successful shop lock toggle"""
        mock_player = Mock()
        mock_db.load_player.return_value = mock_player

        mock_gm.toggle_shop_lock.return_value = (True, "Shop locked")

        with patch('routes.game_actions.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'locked_shop': True}

            result = toggle_shop_lock(123)

            assert result.status_code == 200
            mock_gm.toggle_shop_lock.assert_called_with(mock_player)