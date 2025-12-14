"""
Tests for game_management.py
"""
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, patch, AsyncMock
from routes.game_management import get_state, start_game, reset_game, surrender_game, init_sample_bots


class TestGetState:
    """Test the get_state function"""

    @patch('routes.game_management.db_manager')
    def test_get_state_player_exists(self, mock_db):
        """Test get_state when player exists"""
        mock_player = Mock()
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        with patch('routes.game_management.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 10, 'level': 1, 'synergies': []}

            result = get_state(123)

            assert result.status_code == 200
            data = result.get_json()
            assert data['gold'] == 10
            mock_db.load_player.assert_called_with(123)

    @patch('routes.game_management.db_manager')
    def test_get_state_player_not_found(self, mock_db):
        """Test get_state when player doesn't exist"""
        mock_db.load_player.return_value = None

        result = get_state(123)

        assert result.status_code == 404
        data = result.get_json()
        assert data['error'] == 'No game found'
        assert data['needs_start'] is True


class TestStartGame:
    """Test the start_game function"""

    @patch('routes.game_management.db_manager')
    @patch('routes.game_management.game_manager')
    def test_start_game_new_player(self, mock_gm, mock_db):
        """Test start_game for new player"""
        mock_db.load_player.return_value = None

        mock_player = Mock()
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_gm.create_new_player.return_value = mock_player

        with patch('routes.game_management.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 10, 'level': 1, 'new_player': True}

            result = start_game(123)

            assert result.status_code == 200
            mock_gm.create_new_player.assert_called_with(123)
            mock_gm.generate_shop.assert_called_with(mock_player)
            mock_db.save_player.assert_called_with(mock_player)

    @patch('routes.game_management.db_manager')
    @patch('routes.game_management.game_manager')
    def test_start_game_existing_player_no_shop(self, mock_gm, mock_db):
        """Test start_game for existing player without shop"""
        mock_player = Mock()
        mock_player.last_shop = None
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        with patch('routes.game_management.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 10, 'level': 1, 'shop_generated': True}

            result = start_game(123)

            assert result.status_code == 200
            mock_gm.generate_shop.assert_called_with(mock_player)
            mock_db.save_player.assert_called_with(mock_player)


class TestResetGame:
    """Test the reset_game function"""

    @patch('routes.game_management.db_manager')
    @patch('routes.game_management.game_manager')
    def test_reset_game_success(self, mock_gm, mock_db):
        """Test successful game reset"""
        mock_player = Mock()
        mock_player.wins = 5
        mock_db.load_player.return_value = mock_player

        mock_new_player = Mock()
        mock_new_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_gm.create_new_player.return_value = mock_new_player

        with patch('routes.game_management.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 10, 'level': 1, 'reset': True}

            result = reset_game(123)

            assert result.status_code == 200
            data = result.get_json()
            assert 'message' in data
            mock_gm.create_new_player.assert_called_with(123)
            mock_db.save_to_leaderboard.assert_called_once()

    @patch('routes.game_management.db_manager')
    def test_reset_game_player_not_found(self, mock_db):
        """Test reset_game when player doesn't exist"""
        mock_db.load_player.return_value = None

        result = reset_game(123)

        assert result.status_code == 404
        assert result.get_json()['error'] == 'No game found'


class TestSurrenderGame:
    """Test the surrender_game function"""

    @patch('routes.game_management.db_manager')
    @patch('routes.game_management.game_manager')
    def test_surrender_game_success(self, mock_gm, mock_db):
        """Test successful game surrender"""
        mock_player = Mock()
        mock_player.losses = 2
        mock_db.load_player.return_value = mock_player

        mock_new_player = Mock()
        mock_new_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_gm.create_new_player.return_value = mock_new_player

        with patch('routes.game_management.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 10, 'level': 1, 'surrendered': True}

            result = surrender_game(123)

            assert result.status_code == 200
            data = result.get_json()
            assert 'message' in data
            mock_gm.create_new_player.assert_called_with(123)
            mock_db.save_to_leaderboard.assert_called_once()


class TestInitSampleBots:
    """Test the init_sample_bots function"""

    @patch('routes.game_management.db_manager')
    @pytest.mark.asyncio
    async def test_init_sample_bots_needed(self, mock_db):
        """Test init_sample_bots when bots are needed"""
        mock_db.has_system_opponents.return_value = False
        mock_db.add_sample_teams = AsyncMock()

        with patch('routes.game_management.game_manager') as mock_gm:
            mock_gm.data.units = [{'id': 'unit1'}, {'id': 'unit2'}]

            await init_sample_bots()

            mock_db.has_system_opponents.assert_called_once()
            mock_db.add_sample_teams.assert_called_once_with([{'id': 'unit1'}, {'id': 'unit2'}])

    @patch('routes.game_management.db_manager')
    @pytest.mark.asyncio
    async def test_init_sample_bots_not_needed(self, mock_db):
        """Test init_sample_bots when bots already exist"""
        mock_db.has_system_opponents.return_value = True

        await init_sample_bots()

        mock_db.has_system_opponents.assert_called_once()
        mock_db.add_sample_teams.assert_not_called()