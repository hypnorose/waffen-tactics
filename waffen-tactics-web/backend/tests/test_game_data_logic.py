"""
Tests for game data business logic (pure functions, no Flask dependencies)
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.game_data import get_leaderboard_data, get_units_data, get_traits_data


class TestGetLeaderboardData:
    """Test the get_leaderboard_data pure function"""

    @patch('routes.game_data.db_manager')
    def test_get_leaderboard_data_success(self, mock_db):
        """Test successful leaderboard data retrieval"""
        import asyncio
        mock_leaderboard = [
            {'nickname': 'Player1', 'wins': 10, 'losses': 2},
            {'nickname': 'Player2', 'wins': 8, 'losses': 3}
        ]

        # Mock the async method to return a coroutine
        async def mock_get_leaderboard():
            return mock_leaderboard
        mock_db.get_leaderboard = mock_get_leaderboard

        result = get_leaderboard_data()
        assert result == mock_leaderboard

    @patch('routes.game_data.db_manager')
    def test_get_leaderboard_data_empty(self, mock_db):
        """Test leaderboard data retrieval when empty"""
        # Mock the async method to return a coroutine
        async def mock_get_leaderboard():
            return []
        mock_db.get_leaderboard = mock_get_leaderboard

        result = get_leaderboard_data()
        assert result == []


class TestGetUnitsData:
    """Test the get_units_data pure function"""

    @patch('routes.game_data.game_manager')
    def test_get_units_data_success(self, mock_gm):
        """Test successful units data retrieval"""
        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'unit1'
        mock_unit.name = 'Test Unit'
        mock_unit.cost = 1
        mock_unit.factions = ['faction1']
        mock_unit.classes = ['class1']
        mock_unit.role = 'role1'
        mock_unit.role_color = '#ff0000'
        mock_unit.avatar = 'avatar1.png'
        mock_unit.stats = {'hp': 100, 'attack': 20}

        mock_gm.data.units = [mock_unit]

        result = get_units_data()
        assert len(result) == 1
        assert result[0]['id'] == 'unit1'
        assert result[0]['name'] == 'Test Unit'
        assert result[0]['stats'] == {'hp': 100, 'attack': 20}

    @patch('routes.game_data.game_manager')
    def test_get_units_data_fallback_stats(self, mock_gm):
        """Test units data with fallback stats calculation"""
        # Mock unit without stats attribute
        mock_unit = Mock()
        mock_unit.id = 'unit2'
        mock_unit.name = 'Fallback Unit'
        mock_unit.cost = 2
        mock_unit.factions = ['faction2']
        mock_unit.classes = ['class2']
        # No stats attribute - should use fallback

        # Mock unit without role/role_color/avatar
        del mock_unit.role
        del mock_unit.role_color
        del mock_unit.avatar

        mock_gm.data.units = [mock_unit]

        result = get_units_data()
        assert len(result) == 1
        assert result[0]['id'] == 'unit2'
        # Check fallback stats: hp = 80 + (cost * 40) = 80 + 80 = 160
        assert result[0]['stats']['hp'] == 160
        # attack = 20 + (cost * 10) = 20 + 20 = 40
        assert result[0]['stats']['attack'] == 40
        # Check default values
        assert result[0]['role'] is None
        assert result[0]['role_color'] == '#6b7280'
        assert result[0]['avatar'] is None

    @patch('routes.game_data.game_manager')
    def test_get_units_data_empty(self, mock_gm):
        """Test units data retrieval when empty"""
        mock_gm.data.units = []

        result = get_units_data()
        assert result == []


class TestGetTraitsData:
    """Test the get_traits_data pure function"""

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_success(self, mock_gm):
        """Test successful traits data retrieval"""
        mock_trait = {
            'name': 'TestTrait',
            'type': 'faction',
            'description': 'Test description',
            'thresholds': [2, 4, 6],
            'threshold_descriptions': ['desc1', 'desc2', 'desc3'],
            'effects': [{'type': 'stat_buff', 'stat': 'attack', 'value': 10}]
        }

        mock_gm.data.traits = [mock_trait]

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'TestTrait'
        assert result[0]['type'] == 'faction'
        assert result[0]['effects'] == mock_trait['effects']

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_minimal(self, mock_gm):
        """Test traits data with minimal fields"""
        mock_trait = {
            'name': 'MinimalTrait',
            'type': 'class',
            'thresholds': [3, 6],
            'effects': [{'type': 'mana_buff', 'value': 5}]
            # No description or threshold_descriptions
        }

        mock_gm.data.traits = [mock_trait]

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'MinimalTrait'
        assert result[0]['description'] == ''  # Default empty
        assert result[0]['threshold_descriptions'] == []  # Default empty list

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_empty(self, mock_gm):
        """Test traits data retrieval when empty"""
        mock_gm.data.traits = []

        result = get_traits_data()
        assert result == []