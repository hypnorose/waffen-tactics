"""
Tests for game_state_utils.py
"""
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'waffen-tactics', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import asyncio
from unittest.mock import Mock, patch
from waffen_tactics.models.player_state import PlayerState
from routes.game_state_utils import run_async, enrich_player_state


class TestRunAsync:
    """Test the run_async helper function"""

    @pytest.mark.asyncio
    async def test_run_async_with_coro(self):
        """Test that run_async properly executes a coroutine"""
        async def sample_coro():
            return "test_result"

        result = run_async(sample_coro())
        assert result == "test_result"

    @pytest.mark.asyncio
    async def test_run_async_with_exception(self):
        """Test that run_async properly propagates exceptions"""
        async def failing_coro():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_async(failing_coro())


class TestEnrichPlayerState:
    """Test the enrich_player_state function"""

    @patch('routes.game_state_utils.RARITY_ODDS_BY_LEVEL')
    def test_enrich_player_state_basic(self, mock_rarity_odds):
        """Test basic player state enrichment"""
        mock_rarity_odds.__getitem__.return_value = {1: 100, 2: 0, 3: 0, 4: 0, 5: 0}

        # Create a mock player
        player = Mock(spec=PlayerState)
        player.to_dict.return_value = {
            'gold': 10,
            'level': 1,
            'board': [],
            'bench': [],
            'shop': [],
            'wins': 0,
            'losses': 0
        }
        player.level = 1

        result = enrich_player_state(player)

        assert 'synergies' in result
        assert 'shop_odds' in result
        assert result['shop_odds'] == [100, 0, 0, 0, 0]  # Based on mock

    @patch('routes.game_state_utils.RARITY_ODDS_BY_LEVEL')
    def test_enrich_player_state_with_synergies(self, mock_rarity_odds):
        """Test player state enrichment with synergies"""
        mock_rarity_odds.__getitem__.return_value = {1: 100, 2: 0, 3: 0, 4: 0, 5: 0}

        # Mock game_manager and its methods
        with patch('routes.game_state_utils.game_manager') as mock_gm:
            mock_gm.get_board_synergies.return_value = {'TestTrait': (2, 1)}
            mock_gm.data.traits = [{
                'name': 'TestTrait',
                'type': 'faction',
                'thresholds': [2, 4],
                'effects': [{'type': 'stat_buff', 'stat': 'attack', 'value': 10}],
                'description': 'Test trait'
            }]

            # Create a mock player with units on board
            player = Mock(spec=PlayerState)
            player.to_dict.return_value = {
                'gold': 10,
                'level': 1,
                'board': [{'unit_id': 'test_unit', 'instance_id': 'inst1', 'star_level': 1}],
                'bench': [],
                'shop': [],
                'wins': 0,
                'losses': 0
            }
            player.level = 1
            player.board = [Mock(unit_id='test_unit', instance_id='inst1', star_level=1, hp_stacks=0)]

            # Mock unit data
            mock_unit = Mock()
            mock_unit.factions = ['TestTrait']
            mock_unit.classes = []
            mock_unit.stats = Mock(hp=100, attack=20, defense=5, attack_speed=1.0, max_mana=100)

            with patch('routes.game_state_utils.next') as mock_next:
                mock_next.return_value = mock_unit

                result = enrich_player_state(player)

                assert 'synergies' in result
                assert len(result['synergies']) > 0
                synergy = result['synergies'][0]
                assert synergy['name'] == 'TestTrait'
                assert synergy['count'] == 1  # Only one unit, but trait appears once
                assert synergy['tier'] == 1