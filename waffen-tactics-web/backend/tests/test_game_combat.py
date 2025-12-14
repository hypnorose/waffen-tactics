"""
Tests for game_combat.py
"""
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from flask import Response
from routes.game_combat import start_combat


class TestStartCombat:
    """Test the start_combat function"""

    @patch('routes.game_combat.db_manager')
    @patch('routes.game_combat.game_manager')
    @patch('routes.game_combat.CombatSimulator')
    def test_start_combat_success(self, mock_combat_sim, mock_gm, mock_db):
        """Test successful combat start"""
        # Mock player
        mock_player = Mock()
        mock_player.units = [{'id': 'unit1'}]
        mock_player.bench = []
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        # Mock opponent
        mock_opponent = Mock()
        mock_opponent.units = [{'id': 'unit2'}]
        mock_opponent.bench = []
        mock_opponent.to_dict.return_value = {'gold': 15, 'level': 2}
        mock_db.load_random_opponent.return_value = mock_opponent

        # Mock combat simulator
        mock_simulator = Mock()
        mock_simulator.simulate_combat.return_value = {
            'winner': 'player',
            'combat_log': ['Round 1: Player attacks'],
            'player_units': [{'id': 'unit1', 'health': 80}],
            'opponent_units': [{'id': 'unit2', 'health': 0}]
        }
        mock_combat_sim.return_value = mock_simulator

        # Mock game manager
        mock_gm.apply_combat_results.return_value = None

        with patch('routes.game_combat.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 12, 'level': 1, 'combat_complete': True}

            result = start_combat(123)

            assert isinstance(result, Response)
            assert result.status_code == 200
            assert 'text/event-stream' in result.headers.get('Content-Type', '')

    @patch('routes.game_combat.db_manager')
    def test_start_combat_player_not_found(self, mock_db):
        """Test start_combat when player doesn't exist"""
        mock_db.load_player.return_value = None

        result = start_combat(123)

        assert isinstance(result, Response)
        assert result.status_code == 404

    @patch('routes.game_combat.db_manager')
    def test_start_combat_no_opponent(self, mock_db):
        """Test start_combat when no opponent available"""
        mock_player = Mock()
        mock_player.units = [{'id': 'unit1'}]
        mock_db.load_player.return_value = mock_player
        mock_db.load_random_opponent.return_value = None

        result = start_combat(123)

        assert isinstance(result, Response)
        assert result.status_code == 400

    @patch('routes.game_combat.db_manager')
    def test_start_combat_no_units(self, mock_db):
        """Test start_combat when player has no units"""
        mock_player = Mock()
        mock_player.units = []
        mock_db.load_player.return_value = mock_player

        result = start_combat(123)

        assert isinstance(result, Response)
        assert result.status_code == 400

    @patch('routes.game_combat.db_manager')
    @patch('routes.game_combat.game_manager')
    @patch('routes.game_combat.CombatSimulator')
    def test_start_combat_player_win(self, mock_combat_sim, mock_gm, mock_db):
        """Test combat where player wins"""
        # Setup mocks similar to success test
        mock_player = Mock()
        mock_player.units = [{'id': 'unit1'}]
        mock_player.bench = []
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        mock_opponent = Mock()
        mock_opponent.units = [{'id': 'unit2'}]
        mock_opponent.bench = []
        mock_opponent.to_dict.return_value = {'gold': 15, 'level': 2}
        mock_db.load_random_opponent.return_value = mock_opponent

        mock_simulator = Mock()
        mock_simulator.simulate_combat.return_value = {
            'winner': 'player',
            'combat_log': ['Player wins!'],
            'player_units': [{'id': 'unit1', 'health': 100}],
            'opponent_units': [{'id': 'unit2', 'health': 0}]
        }
        mock_combat_sim.return_value = mock_simulator

        mock_gm.apply_combat_results.return_value = None

        with patch('routes.game_combat.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 12, 'level': 1, 'win': True}

            result = start_combat(123)

            assert isinstance(result, Response)
            assert result.status_code == 200
            # Verify win was applied
            mock_gm.apply_combat_results.assert_called_with(mock_player, 'win')

    @patch('routes.game_combat.db_manager')
    @patch('routes.game_combat.game_manager')
    @patch('routes.game_combat.CombatSimulator')
    def test_start_combat_player_loss(self, mock_combat_sim, mock_gm, mock_db):
        """Test combat where player loses"""
        # Setup mocks
        mock_player = Mock()
        mock_player.units = [{'id': 'unit1'}]
        mock_player.bench = []
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        mock_opponent = Mock()
        mock_opponent.units = [{'id': 'unit2'}]
        mock_opponent.bench = []
        mock_opponent.to_dict.return_value = {'gold': 15, 'level': 2}
        mock_db.load_random_opponent.return_value = mock_opponent

        mock_simulator = Mock()
        mock_simulator.simulate_combat.return_value = {
            'winner': 'opponent',
            'combat_log': ['Opponent wins!'],
            'player_units': [{'id': 'unit1', 'health': 0}],
            'opponent_units': [{'id': 'unit2', 'health': 100}]
        }
        mock_combat_sim.return_value = mock_simulator

        mock_gm.apply_combat_results.return_value = None

        with patch('routes.game_combat.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 8, 'level': 1, 'loss': True}

            result = start_combat(123)

            assert isinstance(result, Response)
            assert result.status_code == 200
            # Verify loss was applied
            mock_gm.apply_combat_results.assert_called_with(mock_player, 'loss')

    @patch('routes.game_combat.db_manager')
    @patch('routes.game_combat.game_manager')
    @patch('routes.game_combat.CombatSimulator')
    def test_start_combat_draw(self, mock_combat_sim, mock_gm, mock_db):
        """Test combat that results in a draw"""
        # Setup mocks
        mock_player = Mock()
        mock_player.units = [{'id': 'unit1'}]
        mock_player.bench = []
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        mock_opponent = Mock()
        mock_opponent.units = [{'id': 'unit2'}]
        mock_opponent.bench = []
        mock_opponent.to_dict.return_value = {'gold': 15, 'level': 2}
        mock_db.load_random_opponent.return_value = mock_opponent

        mock_simulator = Mock()
        mock_simulator.simulate_combat.return_value = {
            'winner': 'draw',
            'combat_log': ['Draw!'],
            'player_units': [{'id': 'unit1', 'health': 50}],
            'opponent_units': [{'id': 'unit2', 'health': 50}]
        }
        mock_combat_sim.return_value = mock_simulator

        mock_gm.apply_combat_results.return_value = None

        with patch('routes.game_combat.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 10, 'level': 1, 'draw': True}

            result = start_combat(123)

            assert isinstance(result, Response)
            assert result.status_code == 200
            # Verify draw was applied
            mock_gm.apply_combat_results.assert_called_with(mock_player, 'draw')

    @patch('routes.game_combat.db_manager')
    @patch('routes.game_combat.game_manager')
    @patch('routes.game_combat.CombatSimulator')
    def test_start_combat_with_bench_units(self, mock_combat_sim, mock_gm, mock_db):
        """Test combat with bench units included"""
        # Setup mocks
        mock_player = Mock()
        mock_player.units = [{'id': 'unit1'}]
        mock_player.bench = [{'id': 'bench_unit'}]
        mock_player.to_dict.return_value = {'gold': 10, 'level': 1}
        mock_db.load_player.return_value = mock_player

        mock_opponent = Mock()
        mock_opponent.units = [{'id': 'unit2'}]
        mock_opponent.bench = []
        mock_opponent.to_dict.return_value = {'gold': 15, 'level': 2}
        mock_db.load_random_opponent.return_value = mock_opponent

        mock_simulator = Mock()
        mock_simulator.simulate_combat.return_value = {
            'winner': 'player',
            'combat_log': ['Player wins with bench unit!'],
            'player_units': [{'id': 'unit1', 'health': 100}, {'id': 'bench_unit', 'health': 100}],
            'opponent_units': [{'id': 'unit2', 'health': 0}]
        }
        mock_combat_sim.return_value = mock_simulator

        mock_gm.apply_combat_results.return_value = None

        with patch('routes.game_combat.enrich_player_state') as mock_enrich:
            mock_enrich.return_value = {'gold': 12, 'level': 1, 'bench_used': True}

            result = start_combat(123)

            assert isinstance(result, Response)
            assert result.status_code == 200
            # Verify bench units were included in combat
            args = mock_combat_sim.call_args
            player_units = args[0][0]  # First positional argument
            assert len(player_units) == 2  # unit1 + bench_unit