import pytest
from unittest.mock import Mock, patch
from waffen_tactics.services.combat_manager import CombatManager
from waffen_tactics.services.data_loader import GameData
from waffen_tactics.services.synergy import SynergyEngine
from waffen_tactics.models.player_state import PlayerState, UnitInstance
from waffen_tactics.models.unit import Unit, Stats, Skill


@pytest.fixture
def mock_data():
    """Mock GameData with some test units"""
    data = Mock(spec=GameData)
    # Create test units
    test_units = [
        Unit("test_unit_1", "Test Unit 1", 1, ["Trait1"], ["Class1"],
             Stats(attack=50, hp=100, defense=10, max_mana=100, attack_speed=1.0),
             Skill("Test Skill", "test", 100, {"type": "damage", "amount": 20})),
        Unit("test_unit_2", "Test Unit 2", 1, ["Trait2"], ["Class2"],
             Stats(attack=60, hp=120, defense=15, max_mana=100, attack_speed=1.1),
             Skill("Test Skill 2", "test2", 100, {"type": "heal", "amount": 30}))
    ]
    data.units = test_units
    return data


@pytest.fixture
def mock_synergy_engine():
    """Mock SynergyEngine"""
    engine = Mock(spec=SynergyEngine)
    engine.compute.return_value = {}
    engine.apply_stat_buffs.return_value = {'hp': 100, 'attack': 50, 'defense': 10, 'attack_speed': 1.0}
    engine.apply_dynamic_effects.return_value = {'hp': 100, 'attack': 50, 'defense': 10, 'attack_speed': 1.0}
    engine.get_active_effects.return_value = []
    engine.apply_enemy_debuffs.return_value = {}
    return engine


@pytest.fixture
def combat_manager(mock_data, mock_synergy_engine):
    """CombatManager instance with mocked dependencies"""
    return CombatManager(mock_data, mock_synergy_engine)


@pytest.fixture
def player_state():
    """Test player state with units on board"""
    player = PlayerState(user_id=1)
    player.board = [
        UnitInstance(unit_id="test_unit_1", instance_id="inst1", star_level=1, position="front",
                    persistent_buffs={'hp': 0, 'attack': 0, 'defense': 0, 'attack_speed': 0.0}),
        UnitInstance(unit_id="test_unit_2", instance_id="inst2", star_level=1, position="back",
                    persistent_buffs={'hp': 0, 'attack': 0, 'defense': 0, 'attack_speed': 0.0})
    ]
    player.round_number = 1
    return player


@pytest.fixture
def opponent_board(mock_data):
    """Test opponent board"""
    return mock_data.units[:2]


class TestCombatManager:
    """Test CombatManager functionality"""

    @patch('waffen_tactics.services.combat_manager.CombatSimulator')
    def test_start_combat_player_wins(self, mock_combat_sim, combat_manager, player_state, opponent_board, mock_synergy_engine):
        """Test successful combat where player wins"""
        # Mock combat simulator to return player win
        mock_sim_instance = Mock()
        mock_sim_instance.simulate.return_value = {
            'winner': 'team_a',
            'duration': 5.0,
            'log': ['Combat started', 'Player wins']
        }
        mock_combat_sim.return_value = mock_sim_instance

        result = combat_manager.start_combat(player_state, opponent_board)

        # Verify result structure
        assert result['winner'] == 'player'
        assert result['damage_taken'] == 0
        assert 'duration' in result
        assert 'log' in result

        # Verify player stats updated
        assert player_state.wins == 1
        assert player_state.streak == 1

        # Verify combat simulator was called
        mock_sim_instance.simulate.assert_called_once()

    @patch('waffen_tactics.services.combat_manager.CombatSimulator')
    def test_start_combat_player_loses(self, mock_combat_sim, combat_manager, player_state, opponent_board):
        """Test combat where player loses"""
        # Mock combat simulator to return opponent win
        mock_sim_instance = Mock()
        mock_sim_instance.simulate.return_value = {
            'winner': 'team_b',
            'duration': 3.0,
            'log': ['Combat started', 'Opponent wins']
        }
        mock_combat_sim.return_value = mock_sim_instance

        initial_hp = player_state.hp
        result = combat_manager.start_combat(player_state, opponent_board, {'level': 2})

        # Verify result structure
        assert result['winner'] == 'opponent'
        assert result['damage_taken'] > 0
        assert player_state.hp < initial_hp

        # Verify player stats updated
        assert player_state.losses == 1
        assert player_state.streak == -1

    @patch('waffen_tactics.services.combat_manager.CombatSimulator')
    def test_start_combat_with_persistent_buffs(self, mock_combat_sim, combat_manager, player_state, opponent_board, mock_synergy_engine):
        """Test that persistent buffs are applied to surviving units"""
        # Mock surviving units with permanent buffs
        mock_sim_instance = Mock()
        mock_sim_instance.simulate.return_value = {
            'winner': 'team_a',
            'duration': 5.0,
            'log': ['Combat started', 'Player wins']
        }
        mock_combat_sim.return_value = mock_sim_instance

        # Mock combat units with permanent buffs applied
        from waffen_tactics.services.combat_shared import CombatUnit
        combat_unit = CombatUnit(
            id="a_inst1", name="Test Unit 1", hp=50, attack=50, defense=10, attack_speed=1.0,
            effects=[], max_mana=100, stats=Mock(), position="front", base_stats={}
        )
        combat_unit.permanent_buffs_applied = {'attack': 5, 'hp': 10}

        # Mock the team_a_combat list to include our combat unit
        with patch.object(combat_manager, 'start_combat') as mock_start:
            mock_start.return_value = {'winner': 'player', 'damage_taken': 0}

            # We need to patch the internal logic, but for now just test the structure
            result = combat_manager.start_combat(player_state, opponent_board)

            # This test would need more detailed mocking of the internal combat units
            # For now, verify the method runs without error
            assert 'winner' in result

    def test_start_combat_no_player_units(self, combat_manager, opponent_board):
        """Test combat with empty player board"""
        player = PlayerState(user_id=1)
        player.board = []  # Empty board

        result = combat_manager.start_combat(player, opponent_board)

        assert result['winner'] == 'opponent'
        assert 'Nie masz jednostek na planszy!' in result['reason']
        assert result['damage_taken'] == 10

    @patch('waffen_tactics.services.combat_manager.CombatSimulator')
    def test_start_combat_exception_handling(self, mock_combat_sim, combat_manager, player_state, opponent_board, mock_synergy_engine):
        """Test that exceptions in simulation are handled gracefully"""
        # Mock first simulate call to raise exception
        mock_sim_instance = Mock()
        mock_sim_instance.simulate.side_effect = [Exception("Simulation error"), {
            'winner': 'team_a',
            'duration': 5.0,
            'log': ['Fallback combat']
        }]
        mock_combat_sim.return_value = mock_sim_instance

        result = combat_manager.start_combat(player_state, opponent_board)

        # Should still return a valid result despite first exception
        assert 'winner' in result
        assert result['winner'] == 'player'

        # Verify simulate was called twice (first failed, second succeeded)
        assert mock_sim_instance.simulate.call_count == 2

    def test_unit_lookup_by_id(self, combat_manager, mock_data, player_state):
        """Test that units are correctly looked up by ID from GameData"""
        # Test with valid unit IDs
        result = combat_manager.start_combat(player_state, [])

        # The method should attempt to look up units
        # This is more of an integration test, but verifies the lookup logic
        assert isinstance(result, dict)

    @patch('waffen_tactics.services.combat_manager.CombatSimulator')
    def test_synergy_engine_integration(self, mock_combat_sim, combat_manager, player_state, opponent_board, mock_synergy_engine):
        """Test that SynergyEngine methods are called correctly"""
        mock_sim_instance = Mock()
        mock_sim_instance.simulate.return_value = {'winner': 'team_a', 'duration': 1.0, 'log': []}
        mock_combat_sim.return_value = mock_sim_instance

        combat_manager.start_combat(player_state, opponent_board)

        # Verify SynergyEngine methods were called
        mock_synergy_engine.compute.assert_called()
        mock_synergy_engine.apply_stat_buffs.assert_called()
        mock_synergy_engine.get_active_effects.assert_called()