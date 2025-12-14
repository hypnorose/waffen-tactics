"""
Tests for game_data.py
"""
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, patch
from routes.game_data import get_leaderboard, get_units, get_traits


class TestGetLeaderboard:
    """Test the get_leaderboard function"""

    @patch('routes.game_data.db_manager')
    def test_get_leaderboard_success(self, mock_db):
        """Test successful leaderboard retrieval"""
        mock_leaderboard = [
            {'nickname': 'Player1', 'wins': 10, 'losses': 2},
            {'nickname': 'Player2', 'wins': 8, 'losses': 3}
        ]
        mock_db.get_leaderboard.return_value = mock_leaderboard

        result = get_leaderboard()

        assert result.status_code == 200
        data = result.get_json()
        assert data == mock_leaderboard
        mock_db.get_leaderboard.assert_called_once()

    @patch('routes.game_data.db_manager')
    def test_get_leaderboard_empty(self, mock_db):
        """Test leaderboard retrieval when empty"""
        mock_db.get_leaderboard.return_value = []

        result = get_leaderboard()

        assert result.status_code == 200
        data = result.get_json()
        assert data == []


class TestGetUnits:
    """Test the get_units function"""

    @patch('routes.game_data.game_manager')
    def test_get_units_success(self, mock_gm):
        """Test successful units retrieval"""
        mock_units = [
            {
                'id': 'unit1',
                'name': 'Test Unit',
                'cost': 1,
                'stats': {'hp': 100, 'attack': 20}
            }
        ]
        mock_gm.data.units = mock_units

        result = get_units()

        assert result.status_code == 200
        data = result.get_json()
        assert len(data) == 1
        assert data[0]['id'] == 'unit1'

    @patch('routes.game_data.game_manager')
    def test_get_units_empty(self, mock_gm):
        """Test units retrieval when empty"""
        mock_gm.data.units = []

        result = get_units()

        assert result.status_code == 200
        data = result.get_json()
        assert data == []


class TestGetTraits:
    """Test the get_traits function"""

    @patch('routes.game_data.game_manager')
    def test_get_traits_success(self, mock_gm):
        """Test successful traits retrieval"""
        mock_traits = [
            {
                'name': 'TestTrait',
                'type': 'faction',
                'thresholds': [2, 4],
                'effects': [{'type': 'stat_buff', 'stat': 'attack', 'value': 10}]
            }
        ]
        mock_gm.data.traits = mock_traits

        result = get_traits()

        assert result.status_code == 200
        data = result.get_json()
        assert len(data) == 1
        assert data[0]['name'] == 'TestTrait'
        assert data[0]['type'] == 'faction'

    @patch('routes.game_data.game_manager')
    def test_get_traits_empty(self, mock_gm):
        """Test traits retrieval when empty"""
        mock_gm.data.traits = []

        result = get_traits()

        assert result.status_code == 200
        data = result.get_json()
        assert data == []

    @patch('routes.game_data.game_manager')
    def test_get_traits_with_effects(self, mock_gm):
        """Test traits retrieval with complex effects"""
        mock_traits = [
            {
                'name': 'ComplexTrait',
                'type': 'class',
                'thresholds': [3, 5, 7],
                'effects': [
                    {'type': 'stat_buff', 'stat': 'hp', 'value': 50, 'is_percentage': False},
                    {'type': 'mana_regen', 'value': 5}
                ],
                'description': 'A complex trait with multiple effects'
            }
        ]
        mock_gm.data.traits = mock_traits

        result = get_traits()

        assert result.status_code == 200
        data = result.get_json()
        assert len(data) == 1
        trait = data[0]
        assert trait['name'] == 'ComplexTrait'
        assert len(trait['effects']) == 2
        assert trait['effects'][0]['type'] == 'stat_buff'
        assert trait['effects'][1]['type'] == 'mana_regen'