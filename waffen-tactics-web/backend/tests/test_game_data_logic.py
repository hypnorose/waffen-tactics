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
        del mock_unit.stats

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
            'modular_effects': [
                [{'rewards': [{'stat': 'attack', 'value': 10}], 'conditions': {}}],
                [{'rewards': [{'stat': 'defense', 'value': 20}], 'conditions': {}}],
                [{'rewards': [{'stat': 'health', 'value': 30}], 'conditions': {}}]
            ]
        }

        mock_gm.synergy_engine.trait_effects = {'test_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'TestTrait'
        assert result[0]['type'] == 'faction'
        assert result[0]['threshold_descriptions'] == ['desc1', 'desc2', 'desc3']
        assert result[0]['modular_effects'] == mock_trait['modular_effects']

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_with_placeholder_replacement(self, mock_gm):
        """Test traits data with placeholder replacement in threshold_descriptions"""
        mock_trait = {
            'name': 'BuffTrait',
            'type': 'class',
            'description': 'Buff description',
            'thresholds': [2, 4],
            'threshold_descriptions': ['+<rewards.value> attack', '+<rewards.value>% defense'],
            'modular_effects': [
                [{'rewards': [{'stat': 'attack', 'value': 25}], 'conditions': {}}],
                [{'rewards': [{'stat': 'defense', 'value': 50}], 'conditions': {'chance_percent': 75}}]
            ]
        }

        mock_gm.synergy_engine.trait_effects = {'buff_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'BuffTrait'
        # Check that placeholders are replaced
        assert result[0]['threshold_descriptions'][0] == '+25 attack'
        assert result[0]['threshold_descriptions'][1] == '+50% defense'

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_with_conditions_placeholder(self, mock_gm):
        """Test traits data with conditions placeholder replacement"""
        mock_trait = {
            'name': 'ChanceTrait',
            'type': 'faction',
            'description': 'Chance description',
            'thresholds': [3],
            'threshold_descriptions': ['<conditions.chance_percent>% chance for +<rewards.value> gold'],
            'modular_effects': [
                [{'rewards': [{'stat': 'resource', 'value': 1}], 'conditions': {'chance_percent': 25}}]
            ]
        }

        mock_gm.synergy_engine.trait_effects = {'chance_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['threshold_descriptions'][0] == '25% chance for +1 gold'

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_default_template_generation(self, mock_gm):
        """Test traits data with default template generation when no threshold_descriptions"""
        mock_trait = {
            'name': 'DefaultTrait',
            'type': 'class',
            'description': 'Default description',
            'thresholds': [2, 4],
            'threshold_descriptions': [],  # Empty, should use default template
            'modular_effects': [
                [{'rewards': [{'stat': 'attack', 'value': 15}], 'conditions': {}}],
                [{'rewards': [{'stat': 'defense', 'value': 30}], 'conditions': {}}]
            ]
        }

        mock_gm.synergy_engine.trait_effects = {'default_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'DefaultTrait'
        # Check default template: "+<rewards.value> <stat>"
        assert result[0]['threshold_descriptions'][0] == '+15 attack'
        assert result[0]['threshold_descriptions'][1] == '+30 defense'

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_fallback_to_trait_description(self, mock_gm):
        """Test traits data fallback to trait description when no effects"""
        mock_trait = {
            'name': 'FallbackTrait',
            'type': 'faction',
            'description': 'Fallback description',
            'thresholds': [2],
            'threshold_descriptions': [],
            'modular_effects': [[]]  # Empty effects list
        }

        mock_gm.synergy_engine.trait_effects = {'fallback_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['threshold_descriptions'][0] == 'Fallback description'

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_minimal(self, mock_gm):
        """Test traits data with minimal fields"""
        mock_trait = {
            'name': 'MinimalTrait',
            'type': 'class',
            'thresholds': [3, 6],
            'modular_effects': [
                [{'rewards': [{'stat': 'mana_regen', 'value': 5}], 'conditions': {}}],
                [{'rewards': [{'stat': 'energy_regen', 'value': 10}], 'conditions': {}}]
            ]
            # No description or threshold_descriptions
        }

        mock_gm.synergy_engine.trait_effects = {'minimal_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'MinimalTrait'
        assert result[0]['description'] == ''  # Default empty
        # Should generate default templates
        assert result[0]['threshold_descriptions'][0] == '+5 mana_regen'
        assert result[0]['threshold_descriptions'][1] == '+10 energy_regen'

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_empty(self, mock_gm):
        """Test traits data retrieval when empty"""
        mock_gm.synergy_engine.trait_effects = {}

        result = get_traits_data()
        assert result == []

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_with_legacy_v_placeholder(self, mock_gm):
        """Test traits data with legacy <v> placeholder replacement"""
        mock_trait = {
            'name': 'LegacyTrait',
            'type': 'faction',
            'description': 'Legacy description',
            'thresholds': [3],
            'threshold_descriptions': ['+<v> defense per second'],
            'modular_effects': [
                [{'rewards': [{'stat': 'defense', 'value': 5}], 'conditions': {}}]
            ]
        }

        mock_gm.synergy_engine.trait_effects = {'legacy_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['threshold_descriptions'][0] == '+5 defense per second'
        """Test traits data with multiple traits"""
        mock_trait1 = {
            'name': 'Trait1',
            'type': 'faction',
            'description': 'Description 1',
            'thresholds': [2],
            'threshold_descriptions': ['+10 attack'],
            'modular_effects': [[{'rewards': [{'stat': 'attack', 'value': 10}], 'conditions': {}}]]
        }
        mock_trait2 = {
            'name': 'Trait2',
            'type': 'class',
            'description': 'Description 2',
            'thresholds': [3],
            'threshold_descriptions': [],
            'modular_effects': [[{'rewards': [{'stat': 'defense', 'value': 20}], 'conditions': {}}]]
        }

        mock_gm.synergy_engine.trait_effects = {
            'trait1': mock_trait1,
            'trait2': mock_trait2
        }

        result = get_traits_data()
        assert len(result) == 2
        # Results should be in insertion order (dict.values())
        trait_names = [t['name'] for t in result]
        assert 'Trait1' in trait_names
        assert 'Trait2' in trait_names

    @patch('routes.game_data.game_manager')
    def test_get_traits_data_with_array_indexed_placeholders(self, mock_gm):
        """Test traits data with array-indexed placeholder replacement"""
        mock_trait = {
            'name': 'MultiRewardTrait',
            'type': 'faction',
            'description': 'Multiple rewards description',
            'thresholds': [2],
            'threshold_descriptions': [
                '+<rewards.value[0]> ataku i +<rewards.value[1]> obrony po zabiciu wroga'
            ],
            'modular_effects': [[{
                'rewards': [
                    {'type': 'stat_buff', 'stat': 'attack', 'value': 5},
                    {'type': 'stat_buff', 'stat': 'defense', 'value': 8}
                ],
                'conditions': {}
            }]]
        }

        mock_gm.synergy_engine.trait_effects = {'multi_reward_trait': mock_trait}

        result = get_traits_data()
        assert len(result) == 1
        assert result[0]['name'] == 'MultiRewardTrait'
        assert result[0]['threshold_descriptions'][0] == '+5 ataku i +8 obrony po zabiciu wroga'


class TestGetTraitsRoute:
    """Test the get_traits Flask route function"""

    def test_get_traits_route_success(self, client, flask_app_context):
        """Test successful traits route response"""
        with patch('routes.game_data.get_traits_data') as mock_get_traits:
            mock_traits = [
                {
                    'name': 'TestTrait',
                    'type': 'faction',
                    'description': 'Test description',
                    'thresholds': [2, 4],
                    'threshold_descriptions': ['+10 attack', '+20 defense'],
                    'modular_effects': [[{'rewards': [{'stat': 'attack', 'value': 10}], 'conditions': {}}]]
                }
            ]
            mock_get_traits.return_value = mock_traits

            response = client.get('/game/traits')
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_traits

    def test_get_traits_route_empty(self, client, flask_app_context):
        """Test traits route with empty data"""
        with patch('routes.game_data.get_traits_data') as mock_get_traits:
            mock_get_traits.return_value = []

            response = client.get('/game/traits')
            assert response.status_code == 200
            data = response.get_json()
            assert data == []


class TestGetUnitsRoute:
    """Test the get_units Flask route function"""

    def test_get_units_route_success(self, client, flask_app_context):
        """Test successful units route response"""
        with patch('routes.game_data.get_units_data') as mock_get_units:
            mock_units = [
                {
                    'id': 'unit1',
                    'name': 'Test Unit',
                    'cost': 1,
                    'factions': ['faction1'],
                    'classes': ['class1'],
                    'stats': {'hp': 100, 'attack': 20}
                }
            ]
            mock_get_units.return_value = mock_units

            response = client.get('/game/units')
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_units


class TestGetLeaderboardRoute:
    """Test the get_leaderboard Flask route function"""

    def test_get_leaderboard_route_success(self, client, flask_app_context):
        """Test successful leaderboard route response"""
        with patch('routes.game_routes.get_leaderboard_data') as mock_get_leaderboard:
            mock_leaderboard = [
                {'nickname': 'Player1', 'wins': 10, 'losses': 2},
                {'nickname': 'Player2', 'wins': 8, 'losses': 3}
            ]
            mock_get_leaderboard.return_value = mock_leaderboard

            response = client.get('/game/leaderboard')
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_leaderboard

    def test_get_leaderboard_route_with_period(self, client, flask_app_context):
        """Test leaderboard route with period parameter"""
        with patch('routes.game_routes.get_leaderboard_data') as mock_get_leaderboard:
            mock_leaderboard = [{'nickname': 'Player1', 'wins': 5, 'losses': 1}]
            mock_get_leaderboard.return_value = mock_leaderboard

            response = client.get('/game/leaderboard?period=all')
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_leaderboard
            mock_get_leaderboard.assert_called_with(period='all')