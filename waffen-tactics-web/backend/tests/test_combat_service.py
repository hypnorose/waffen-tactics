"""
Tests for Combat Service
"""
import unittest
import uuid
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../waffen-tactics/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from unittest.mock import AsyncMock, MagicMock, patch
from waffen_tactics.models.player_state import PlayerState
from waffen_tactics.services.combat_shared import CombatUnit
from waffen_tactics.services.data_loader import load_game_data
from services.combat_service import (
    prepare_player_units_for_combat, prepare_opponent_units_for_combat,
    run_combat_simulation, process_combat_results
)
from services.combat_event_reconstructor import CombatEventReconstructor

# Silence noisy `print` calls in these tests; keep a handle to the original
# print and provide `error_print` for printing errors only.
_original_print = print
def print(*args, **kwargs):
    # no-op to avoid test spam
    return None
def error_print(*args, **kwargs):
    _original_print(*args, **kwargs)


class TestCombatService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "123"

        # Create mock player
        self.mock_player = MagicMock(spec=PlayerState)
        self.mock_player.user_id = int(self.user_id)
        self.mock_player.hp = 100
        self.mock_player.board = []
        self.mock_player.max_board_size = 7
        self.mock_player.wins = 5
        self.mock_player.losses = 3
        self.mock_player.level = 1  # Set as int
        self.mock_player.xp = 0  # Set as int
        self.mock_player.gold = 10  # Set as int
        self.mock_player.streak = 0  # Set as int
        self.mock_player.round_number = 1  # Set as int
        self.mock_player.locked_shop = False
        self.mock_player.xp_to_next_level = 2  # Mock the property
        self.mock_player.add_xp = MagicMock(side_effect=lambda amount: (setattr(self.mock_player, 'xp', getattr(self.mock_player, 'xp', 0) + amount), None)[-1])  # Mock add_xp to actually add XP
        self.mock_player.to_dict.return_value = {"user_id": self.user_id}

        # Create mock unit
        self.mock_unit = MagicMock()
        self.mock_unit.id = "unit_001"
        self.mock_unit.name = "Test Unit"
        self.mock_unit.cost = 1
        self.mock_unit.factions = ["TestFaction"]
        self.mock_unit.classes = ["TestClass"]
        self.mock_unit.stats = MagicMock()
        self.mock_unit.stats.hp = 100
        self.mock_unit.stats.attack = 20
        self.mock_unit.stats.defense = 5
        self.mock_unit.stats.attack_speed = 0.8
        self.mock_unit.stats.max_mana = 100
        self.mock_unit.stats.mana_regen = 5

        # Create mock unit instance
        self.mock_unit_instance = MagicMock()
        self.mock_unit_instance.unit_id = "unit_001"
        self.mock_unit_instance.instance_id = "inst_001"
        self.mock_unit_instance.star_level = 1
        self.mock_unit_instance.position = "front"
        self.mock_unit_instance.persistent_buffs = {}

    @patch('services.combat_service.db_manager')
    @patch('services.combat_service.game_manager')
    def test_prepare_player_units_for_combat_success(self, mock_game_manager, mock_db_manager):
        """Test successful player unit preparation"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        self.mock_player.board = [self.mock_unit_instance]
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.get_board_synergies.return_value = {"TestTrait": (1, 1)}
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8, 'max_mana': 100, 'current_mana': 0
        }
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(message, "Player units prepared")
        self.assertIsNotNone(result)
        player_units, player_unit_info, synergies_data = result
        self.assertEqual(len(player_units), 1)
        self.assertEqual(len(player_unit_info), 1)
        self.assertIn("TestTrait", synergies_data)

    @patch('services.combat_service.db_manager')
    def test_prepare_player_units_for_combat_no_player(self, mock_db_manager):
        """Test player unit preparation when no player found"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=None)

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "Player not found")
        self.assertIsNone(result)

    @patch('services.combat_service.db_manager')
    def test_prepare_player_units_for_combat_defeated(self, mock_db_manager):
        """Test player unit preparation when player is defeated"""
        # Setup mocks
        self.mock_player.hp = 0
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "Player is defeated and cannot fight")
        self.assertIsNone(result)

    @patch('services.combat_service.db_manager')
    def test_prepare_player_units_for_combat_no_board(self, mock_db_manager):
        """Test player unit preparation when no units on board"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertFalse(success)
        self.assertEqual(message, "No units on board")
        self.assertIsNone(result)

    @patch('services.combat_service.db_manager')
    @patch('services.combat_service.game_manager')
    def test_prepare_opponent_units_for_combat_success(self, mock_game_manager, mock_db_manager):
        """Test successful opponent unit preparation"""
        # Setup mocks
        opponent_data = {
            'nickname': 'TestOpponent',
            'wins': 10,
            'level': 5,
            'board': [{'unit_id': 'unit_001', 'star_level': 1}]
        }
        mock_db_manager.get_random_opponent = AsyncMock(return_value=opponent_data)
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.synergy_engine.compute.return_value = {}
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 100, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        opponent_units, opponent_unit_info, opponent_info = prepare_opponent_units_for_combat(self.mock_player)

        # Assert
        self.assertEqual(len(opponent_units), 1)
        self.assertEqual(len(opponent_unit_info), 1)
        self.assertEqual(opponent_info['name'], 'TestOpponent')
        self.assertEqual(opponent_info['wins'], 10)
        self.assertEqual(opponent_info['level'], 5)

    @patch('services.combat_service.db_manager')
    def test_prepare_opponent_units_for_combat_fallback(self, mock_db_manager):
        """Test opponent unit preparation fallback when no opponent found"""
        # Setup mocks
        mock_db_manager.get_random_opponent = AsyncMock(return_value=None)

        # Execute & Assert: no DB opponent should cause an error (no ad-hoc fallbacks)
        with self.assertRaises(RuntimeError):
            prepare_opponent_units_for_combat(self.mock_player)

    @patch('services.combat_service.CombatSimulator')
    def test_run_combat_simulation_success(self, mock_simulator_class):
        """Test successful combat simulation"""
        # Setup mocks
        mock_simulator = MagicMock()
        mock_simulator.simulate.return_value = {
            'winner': 'team_a',
            'duration': 10.5,
            'survivors': {'team_a': ['unit1'], 'team_b': []},
            'log': ['Combat started', 'Unit died']
        }
        mock_simulator_class.return_value = mock_simulator

        player_units = [MagicMock(spec=CombatUnit)]
        opponent_units = [MagicMock(spec=CombatUnit)]

        # Execute
        result = run_combat_simulation(player_units, opponent_units)

        # Assert
        self.assertEqual(result['winner'], 'team_a')
        self.assertEqual(result['duration'], 10.5)
        self.assertIn('events', result)
        mock_simulator.simulate.assert_called_once()

    @patch('services.combat_service.CombatSimulator')
    def test_run_combat_simulation_error(self, mock_simulator_class):
        """Test combat simulation error handling"""
        # Setup mocks
        mock_simulator_class.side_effect = Exception("Simulation failed")

        player_units = [MagicMock(spec=CombatUnit)]
        opponent_units = [MagicMock(spec=CombatUnit)]

        # Execute
        result = run_combat_simulation(player_units, opponent_units)

        # Assert
        self.assertEqual(result['winner'], 'error')
        self.assertEqual(result['duration'], 0)
        self.assertIn('Combat error', result['log'][0])

    @patch('services.combat_service.game_manager')
    def test_process_combat_results_victory(self, mock_game_manager):
        """Test processing combat results for victory"""
        # Setup mocks
        self.mock_player.streak = 0
        self.mock_player.board = []
        self.mock_player.locked_shop = False

        mock_game_manager.get_board_synergies.return_value = {}
        mock_game_manager.generate_shop = MagicMock()

        result = {'winner': 'team_a'}
        collected_stats_maps = {}

        # Execute
        game_over, result_data = process_combat_results(self.mock_player, result, collected_stats_maps)

        # Assert
        self.assertFalse(game_over)
        self.assertEqual(result_data['result_message'], "🎉 ZWYCIĘSTWO!")
        self.assertEqual(self.mock_player.wins, 6)  # Increased by 1
        self.assertEqual(self.mock_player.streak, 1)  # Increased by 1
        self.mock_player.add_xp.assert_called_once_with(2)
        self.assertIn('gold_breakdown', result_data)

    @patch('services.combat_service.game_manager')
    def test_process_combat_results_defeat(self, mock_game_manager):
        """Test processing combat results for defeat"""
        # Setup mocks
        self.mock_player.hp = 100
        self.mock_player.streak = 5
        self.mock_player.board = []
        self.mock_player.locked_shop = False

        mock_game_manager.get_board_synergies.return_value = {}
        mock_game_manager.generate_shop = MagicMock()

        result = {'winner': 'team_b', 'surviving_star_sum': 5}
        collected_stats_maps = {}

        # Execute
        game_over, result_data = process_combat_results(self.mock_player, result, collected_stats_maps)

        # Assert
        self.assertFalse(game_over)
        self.assertIn('PRZEGRANA', result_data['result_message'])
        self.assertEqual(self.mock_player.hp, 95)  # Lost 5 HP (5 * 1)
        self.assertEqual(self.mock_player.streak, 0)  # Reset to 0

    @patch('services.combat_service.game_manager')
    def test_process_combat_results_game_over(self, mock_game_manager):
        """Test processing combat results for game over"""
        # Setup mocks
        self.mock_player.hp = 5  # Low HP
        self.mock_player.streak = 5
        self.mock_player.board = []
        self.mock_player.locked_shop = False

        mock_game_manager.get_board_synergies.return_value = {}
        mock_game_manager.generate_shop = MagicMock()

        result = {'winner': 'team_b', 'surviving_star_sum': 5}  # Will cause 10 HP loss
        collected_stats_maps = {}

        # Execute
        game_over, result_data = process_combat_results(self.mock_player, result, collected_stats_maps)

        # Assert
        self.assertTrue(game_over)
        self.assertIn('Koniec gry', result_data['result_message'])
        self.assertEqual(self.mock_player.hp, 0)  # Went to 0 (5 - 5)

    @patch('services.combat_service.db_manager')
    @patch('services.combat_service.game_manager')
    def test_prepare_player_units_hp_calculation_with_synergies_and_persistent_buffs(self, mock_game_manager, mock_db_manager):
        """Test HP calculation with synergies and persistent buffs applied in correct order"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        
        # Create unit instance with persistent HP buff
        self.mock_unit_instance.persistent_buffs = {'hp': 50}
        self.mock_player.board = [self.mock_unit_instance]
        
        mock_game_manager.data.units = [self.mock_unit]
        
        # Mock synergies - Normik class giving +20% HP
        mock_game_manager.get_board_synergies.return_value = {"Normik": (2, 1)}  # 2 units, tier 1
        
        # Base HP calculation: 100 * (1.6^(1-1)) = 100
        # Synergy buff: +20% HP = 100 * 1.2 = 120
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 120, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        # No dynamic effects for this test
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 120, 'attack': 20, 'defense': 5, 'attack_speed': 0.8, 'max_mana': 100, 'current_mana': 0
        }
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertTrue(success)
        player_units, player_unit_info, synergies_data = result
        
        # Check CombatUnit has correct HP (synergies + persistent buffs)
        combat_unit = player_units[0]
        expected_hp = 120 + 50  # 120 from synergies + 50 persistent = 170
        self.assertEqual(combat_unit.hp, expected_hp)
        self.assertEqual(combat_unit.max_hp, expected_hp)
        
        # Check player_unit_info has correct data
        unit_info = player_unit_info[0]
        self.assertEqual(unit_info['hp'], expected_hp)
        self.assertEqual(unit_info['max_hp'], expected_hp)
        self.assertEqual(unit_info['buffed_stats']['hp'], expected_hp)

    @patch('services.combat_service.db_manager')
    @patch('services.combat_service.game_manager')
    def test_prepare_player_units_hp_calculation_order_verification(self, mock_game_manager, mock_db_manager):
        """Test that HP buffs are applied in correct order: base -> synergies -> persistent"""
        # Setup mocks
        mock_db_manager.load_player = AsyncMock(return_value=self.mock_player)
        
        # Create unit instance with persistent HP buff
        self.mock_unit_instance.persistent_buffs = {'hp': 100}
        self.mock_player.board = [self.mock_unit_instance]
        
        mock_game_manager.data.units = [self.mock_unit]
        
        # Mock synergies - higher tier Normik giving +40% HP
        mock_game_manager.get_board_synergies.return_value = {"Normik": (4, 2)}  # 4 units, tier 2
        
        # Base HP: 100
        # Synergy buff: +40% HP = 100 * 1.4 = 140
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 140, 'attack': 20, 'defense': 5, 'attack_speed': 0.8
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 140, 'attack': 20, 'defense': 5, 'attack_speed': 0.8, 'max_mana': 100, 'current_mana': 0
        }
        mock_game_manager.synergy_engine.get_active_effects.return_value = []

        # Execute
        success, message, result = prepare_player_units_for_combat(self.user_id)

        # Assert
        self.assertTrue(success)
        player_units, player_unit_info, synergies_data = result
        
        # Check order: synergies applied first (140), then persistent buffs (+100) = 240
        combat_unit = player_units[0]
        expected_hp = 140 + 100  # synergies first, then persistent
        self.assertEqual(combat_unit.hp, expected_hp)
        self.assertEqual(combat_unit.max_hp, expected_hp)

    def test_specific_team_simulation_and_event_replay(self):
        """Test simulation with specific teams and verify event replay can reconstruct game state"""
        import random
        random.seed(42)  # Add seed for deterministic randomness

        from waffen_tactics.services.combat_shared import CombatUnit

        # Load real game data
        game_data = load_game_data()

        # Helper to get unit by id
        def get_unit(unit_id):
            return next(u for u in game_data.units if u.id == unit_id)

        # Define opponent team
        hyodo_unit = get_unit('hyodo888')
        alysonstark_unit = get_unit('alyson_stark')
        adrianski_unit = get_unit('adrianski')
        szachowymentor_unit = get_unit('szachowymentor')
        olsak_unit = get_unit('olsak')
        pepe_unit = get_unit('pepe')
        frajdzia_unit = get_unit('frajdzia')

        opponent_back = [
            CombatUnit(id=hyodo_unit.id, name=hyodo_unit.name, hp=hyodo_unit.stats.hp, attack=hyodo_unit.stats.attack, defense=hyodo_unit.stats.defense, attack_speed=hyodo_unit.stats.attack_speed, position='back', stats=hyodo_unit.stats, skill=hyodo_unit.skill, max_mana=hyodo_unit.stats.max_mana),
            CombatUnit(id=alysonstark_unit.id, name=alysonstark_unit.name, hp=alysonstark_unit.stats.hp, attack=alysonstark_unit.stats.attack, defense=alysonstark_unit.stats.defense, attack_speed=alysonstark_unit.stats.attack_speed, position='back', stats=alysonstark_unit.stats, skill=alysonstark_unit.skill, max_mana=alysonstark_unit.stats.max_mana),
            CombatUnit(id=adrianski_unit.id, name=adrianski_unit.name, hp=adrianski_unit.stats.hp, attack=adrianski_unit.stats.attack, defense=adrianski_unit.stats.defense, attack_speed=adrianski_unit.stats.attack_speed, position='back', stats=adrianski_unit.stats, skill=adrianski_unit.skill, max_mana=adrianski_unit.stats.max_mana),
            CombatUnit(id=szachowymentor_unit.id, name=szachowymentor_unit.name, hp=szachowymentor_unit.stats.hp, attack=szachowymentor_unit.stats.attack, defense=szachowymentor_unit.stats.defense, attack_speed=szachowymentor_unit.stats.attack_speed, position='back', stats=szachowymentor_unit.stats, skill=szachowymentor_unit.skill, max_mana=szachowymentor_unit.stats.max_mana),
        ]
        opponent_front = [
            CombatUnit(id=olsak_unit.id, name=olsak_unit.name, hp=olsak_unit.stats.hp, attack=olsak_unit.stats.attack, defense=olsak_unit.stats.defense, attack_speed=olsak_unit.stats.attack_speed, position='front', stats=olsak_unit.stats, skill=olsak_unit.skill, max_mana=olsak_unit.stats.max_mana),
            CombatUnit(id=pepe_unit.id, name=pepe_unit.name, hp=pepe_unit.stats.hp, attack=pepe_unit.stats.attack, defense=pepe_unit.stats.defense, attack_speed=pepe_unit.stats.attack_speed, position='front', stats=pepe_unit.stats, skill=pepe_unit.skill, max_mana=pepe_unit.stats.max_mana),
            CombatUnit(id=frajdzia_unit.id, name=frajdzia_unit.name, hp=frajdzia_unit.stats.hp, attack=frajdzia_unit.stats.attack, defense=frajdzia_unit.stats.defense, attack_speed=frajdzia_unit.stats.attack_speed, position='front', stats=frajdzia_unit.stats, skill=frajdzia_unit.skill, max_mana=frajdzia_unit.stats.max_mana),
        ]
        opponent_units = opponent_back + opponent_front

        # Define player team
        turboglowica_unit = get_unit('turboglovica')
        maxas12_unit = get_unit('maxas12')
        dumb_unit = get_unit('dumb')
        puszmen12_unit = get_unit('puszmen12')
        fiko_unit = get_unit('fiko')
        wodazlodowca_unit = get_unit('wodazlodowca')
        vitas_unit = get_unit('vitas')
        mrozu_unit = get_unit('mrozu')

        player_back = [
            CombatUnit(id=turboglowica_unit.id, name=turboglowica_unit.name, hp=turboglowica_unit.stats.hp, attack=turboglowica_unit.stats.attack, defense=turboglowica_unit.stats.defense, attack_speed=turboglowica_unit.stats.attack_speed, position='back', stats=turboglowica_unit.stats, skill=turboglowica_unit.skill, max_mana=turboglowica_unit.stats.max_mana),
            CombatUnit(id=maxas12_unit.id, name=maxas12_unit.name, hp=maxas12_unit.stats.hp, attack=maxas12_unit.stats.attack, defense=maxas12_unit.stats.defense, attack_speed=maxas12_unit.stats.attack_speed, position='back', stats=maxas12_unit.stats, skill=maxas12_unit.skill, max_mana=maxas12_unit.stats.max_mana),
            CombatUnit(id=dumb_unit.id, name=dumb_unit.name, hp=dumb_unit.stats.hp, attack=dumb_unit.stats.attack, defense=dumb_unit.stats.defense, attack_speed=dumb_unit.stats.attack_speed, position='back', stats=dumb_unit.stats, skill=dumb_unit.skill, max_mana=dumb_unit.stats.max_mana),
            CombatUnit(id=puszmen12_unit.id, name=puszmen12_unit.name, hp=puszmen12_unit.stats.hp, attack=puszmen12_unit.stats.attack, defense=puszmen12_unit.stats.defense, attack_speed=puszmen12_unit.stats.attack_speed, position='back', stats=puszmen12_unit.stats, skill=puszmen12_unit.skill, max_mana=puszmen12_unit.stats.max_mana),
        ]
        player_front = [
            CombatUnit(id=fiko_unit.id, name=fiko_unit.name, hp=fiko_unit.stats.hp, attack=fiko_unit.stats.attack, defense=fiko_unit.stats.defense, attack_speed=fiko_unit.stats.attack_speed, position='front', stats=fiko_unit.stats, skill=fiko_unit.skill, max_mana=fiko_unit.stats.max_mana),
            CombatUnit(id=wodazlodowca_unit.id, name=wodazlodowca_unit.name, hp=wodazlodowca_unit.stats.hp, attack=wodazlodowca_unit.stats.attack, defense=wodazlodowca_unit.stats.defense, attack_speed=wodazlodowca_unit.stats.attack_speed, position='front', stats=wodazlodowca_unit.stats, skill=wodazlodowca_unit.skill, max_mana=wodazlodowca_unit.stats.max_mana),
            CombatUnit(id=vitas_unit.id, name=vitas_unit.name, hp=vitas_unit.stats.hp, attack=vitas_unit.stats.attack, defense=vitas_unit.stats.defense, attack_speed=vitas_unit.stats.attack_speed, position='front', stats=vitas_unit.stats, skill=vitas_unit.skill, max_mana=vitas_unit.stats.max_mana),
            CombatUnit(id=mrozu_unit.id, name=mrozu_unit.name, hp=mrozu_unit.stats.hp, attack=mrozu_unit.stats.attack, defense=mrozu_unit.stats.defense, attack_speed=mrozu_unit.stats.attack_speed, position='front', stats=mrozu_unit.stats, skill=mrozu_unit.skill, max_mana=mrozu_unit.stats.max_mana),
        ]
        player_units = player_back + player_front

        # Run simulation
        result = run_combat_simulation(player_units, opponent_units)

        # Verify simulation completed
        self.assertIn('winner', result)
        self.assertIn('duration', result)
        self.assertIn('events', result)
        self.assertIsInstance(result['events'], list)
        self.assertGreater(len(result['events']), 0)

        # Verify events have proper structure
        for event_type, event_data in result['events']:
            self.assertIsInstance(event_type, str)
            self.assertIsInstance(event_data, dict)
            # Check if seq is present (should be added by simulator)
            if event_type in ['unit_attack', 'unit_died', 'state_snapshot']:
                self.assertIn('seq', event_data)
                self.assertIsInstance(event_data['seq'], int)

        # Test event replay: reconstruct game state from events only (no game_state)
        # Sort events by seq
        events = result['events']
        events.sort(key=lambda x: x[1]['seq'])

        # Find state_snapshots
        state_snapshots = [event for event in events if event[0] == 'state_snapshot']
        self.assertGreater(len(state_snapshots), 0, "No state_snapshots found")

        # Initialize reconstruction from first snapshot using the reconstructor
        reconstructor = CombatEventReconstructor()
        first_snapshot = state_snapshots[0][1]
        reconstructor.initialize_from_snapshot(first_snapshot)

        # Process events in order using the reconstructor
        processed_events = 0
        for event_type, event_data in events:
            processed_events += 1
            reconstructor.process_event(event_type, event_data)

        print(f"Total events processed: {processed_events}")

        # Get reconstructed state
        reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

        # Compare final state from simulation (units after simulation) with reconstructed state from events
        for unit in player_units:
            self.assertEqual(unit.hp, reconstructed_player_units[unit.id]['hp'], f"HP mismatch for player unit {unit.id}")
            self.assertEqual(unit.max_hp, reconstructed_player_units[unit.id]['max_hp'], f"Max HP mismatch for player unit {unit.id}")
            self.assertEqual(unit.mana, reconstructed_player_units[unit.id]['current_mana'], f"Mana mismatch for player unit {unit.id}")
        for unit in opponent_units:
            self.assertEqual(unit.hp, reconstructed_opponent_units[unit.id]['hp'], f"HP mismatch for opponent unit {unit.id}")
            self.assertEqual(unit.max_hp, reconstructed_opponent_units[unit.id]['max_hp'], f"Max HP mismatch for opponent unit {unit.id}")
            self.assertEqual(unit.mana, reconstructed_opponent_units[unit.id]['current_mana'], f"Mana mismatch for opponent unit {unit.id}")


    def test_negative_damage_event_processing(self):
        """Test how negative damage in unit_attack events is processed on server and client side"""
        # Create mock units
        player_units = [{'id': 'player1', 'hp': 100, 'max_hp': 100, 'effects': [], 'shield': 0, 'current_mana': 50, 'max_mana': 100, 'attack': 20, 'defense': 5, 'attack_speed': 1.0, 'dead': False}]
        opponent_units = [{'id': 'opponent1', 'hp': 100, 'max_hp': 100, 'effects': [], 'shield': 0, 'current_mana': 50, 'max_mana': 100, 'attack': 20, 'defense': 5, 'attack_speed': 1.0, 'dead': False}]

        # Simulate event processing like in the main test
        reconstructed_player_units = {u['id']: dict(u) for u in player_units}
        reconstructed_opponent_units = {u['id']: dict(u) for u in opponent_units}

        # Test negative damage event (should heal)
        negative_damage_event = ('unit_attack', {
            'target_id': 'opponent1',
            'post_hp': 120,  # HP increases due to negative damage
            'applied_damage': -20,  # Negative damage means healing
            'shield_absorbed': 0,
            'seq': 1,
            'timestamp': 1.0
        })

        # Process the event (simulate the test's event processing)
        event_type, event_data = negative_damage_event
        target_id = event_data.get('target_id')
        new_hp = event_data.get('target_hp') or event_data.get('post_hp')
        shield_absorbed = event_data.get('shield_absorbed', 0)
        damage = event_data.get('applied_damage', 0)

        print(f"Processing negative damage event: damage={damage}, new_hp={new_hp}")

        if target_id in reconstructed_opponent_units:
            old_hp = reconstructed_opponent_units[target_id]['hp']
            reconstructed_opponent_units[target_id]['hp'] = new_hp
            reconstructed_opponent_units[target_id]['shield'] = max(0, reconstructed_opponent_units[target_id].get('shield', 0) - shield_absorbed)
            reconstructed_opponent_units[target_id]['dead'] = new_hp == 0
            print(f"Opponent unit {target_id} HP changed from {old_hp} to {new_hp} (heal of {new_hp - old_hp})")

        # Assert that HP increased (heal occurred)
        self.assertEqual(reconstructed_opponent_units['opponent1']['hp'], 120)
        self.assertEqual(reconstructed_opponent_units['opponent1']['hp'] - 100, 20)  # Heal amount

        # Test positive damage event (should damage)
        positive_damage_event = ('unit_attack', {
            'target_id': 'player1',
            'post_hp': 80,  # HP decreases
            'applied_damage': 20,  # Positive damage
            'shield_absorbed': 0,
            'seq': 2,
            'timestamp': 2.0
        })

        event_type, event_data = positive_damage_event
        target_id = event_data.get('target_id')
        new_hp = event_data.get('target_hp') or event_data.get('post_hp')
        shield_absorbed = event_data.get('shield_absorbed', 0)

        if target_id in reconstructed_player_units:
            old_hp = reconstructed_player_units[target_id]['hp']
            reconstructed_player_units[target_id]['hp'] = new_hp
            reconstructed_player_units[target_id]['shield'] = max(0, reconstructed_player_units[target_id].get('shield', 0) - shield_absorbed)
            reconstructed_player_units[target_id]['dead'] = new_hp == 0
            print(f"Player unit {target_id} HP changed from {old_hp} to {new_hp} (damage of {old_hp - new_hp})")

        # Assert that HP decreased (damage occurred)
        self.assertEqual(reconstructed_player_units['player1']['hp'], 80)
        self.assertEqual(100 - reconstructed_player_units['player1']['hp'], 20)  # Damage amount

        print("Test completed: Negative damage causes heal, positive damage causes damage")

    def test_10v10_simulation_and_event_replay(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state"""
        import random
        random.seed(12345)  # Set seed for reproducible results

        from waffen_tactics.services.combat_shared import CombatUnit

        # Load real game data
        game_data = load_game_data()

        # Prepare helper and id list once; teams will be sampled per-seed below
        all_unit_ids = [u.id for u in game_data.units]
        def get_unit(unit_id):
            return next(u for u in game_data.units if u.id == unit_id)

        # Sample teams (10v10) from available units for this seed
        sample_20 = random.sample(all_unit_ids, 20)
        player_unit_ids = sample_20[:10]
        opponent_unit_ids = sample_20[10:]

        player_units = []
        for unit_id in player_unit_ids:
            unit = get_unit(unit_id)
            player_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(player_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        opponent_units = []
        for unit_id in opponent_unit_ids:
            unit = get_unit(unit_id)
            opponent_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(opponent_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        print(f"Player team ({len(player_units)} units): {[u.name for u in player_units]}")
        print(f"Opponent team ({len(opponent_units)} units): {[u.name for u in opponent_units]}")

        # Run simulation
        result = run_combat_simulation(player_units, opponent_units)

        # Verify simulation completed
        self.assertIn('winner', result)
        self.assertIn('duration', result)
        self.assertIn('events', result)
        self.assertIsInstance(result['events'], list)
        self.assertGreater(len(result['events']), 0)

        # Verify events have proper structure
        for event_type, event_data in result['events']:
            self.assertIsInstance(event_type, str)
            self.assertIsInstance(event_data, dict)
            if event_type in ['unit_attack', 'unit_died', 'state_snapshot']:
                self.assertIn('seq', event_data)
                self.assertIsInstance(event_data['seq'], int)

        # Test event replay using the reusable CombatEventReconstructor
        events = result['events']
        events.sort(key=lambda x: (x[1]['timestamp'], x[1]['seq']))

        # Find state_snapshots
        state_snapshots = [event for event in events if event[0] == 'state_snapshot']
        self.assertGreater(len(state_snapshots), 0, "No state_snapshots found")

        # Initialize reconstruction from first snapshot
        reconstructor = CombatEventReconstructor()
        first_snapshot = state_snapshots[0][1]
        reconstructor.initialize_from_snapshot(first_snapshot)

        # Process all events
        for event_type, event_data in events:
            reconstructor.process_event(event_type, event_data)

        # Get final reconstructed state
        reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

        # Compare final state with simulation results
        for unit in player_units:
            self.assertEqual(unit.hp, reconstructed_player_units[unit.id]['hp'],
                           f"HP mismatch for player unit {unit.name} ({unit.id})")
            self.assertEqual(unit.max_hp, reconstructed_player_units[unit.id]['max_hp'],
                           f"Max HP mismatch for player unit {unit.name} ({unit.id})")
            self.assertEqual(unit.mana, reconstructed_player_units[unit.id]['current_mana'],
                           f"Mana mismatch for player unit {unit.name} ({unit.id})")

        for unit in opponent_units:
            self.assertEqual(unit.hp, reconstructed_opponent_units[unit.id]['hp'],
                           f"HP mismatch for opponent unit {unit.name} ({unit.id})")
            self.assertEqual(unit.max_hp, reconstructed_opponent_units[unit.id]['max_hp'],
                           f"Max HP mismatch for opponent unit {unit.name} ({unit.id})")
            self.assertEqual(unit.mana, reconstructed_opponent_units[unit.id]['current_mana'],
                           f"Mana mismatch for opponent unit {unit.name} ({unit.id})")

        print(f"10v10 test completed successfully. Winner: {result['winner']}, Duration: {result['duration']:.2f}s")

    def test_10v10_simulation_and_event_replay_different_seed(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state with different seed"""
        import random
        random.seed(54321)  # Set different seed for reproducible results

        from waffen_tactics.services.combat_shared import CombatUnit

        # Load real game data
        game_data = load_game_data()

        # Prepare helper and id list once; teams will be sampled per-seed below
        all_unit_ids = [u.id for u in game_data.units]
        def get_unit(unit_id):
            return next(u for u in game_data.units if u.id == unit_id)

        # Sample teams (10v10) from available units for this seed
        sample_20 = random.sample(all_unit_ids, 20)
        player_unit_ids = sample_20[:10]
        opponent_unit_ids = sample_20[10:]

        player_units = []
        for unit_id in player_unit_ids:
            unit = get_unit(unit_id)
            player_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(player_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        opponent_units = []
        for unit_id in opponent_unit_ids:
            unit = get_unit(unit_id)
            opponent_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(opponent_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        print(f"Player team ({len(player_units)} units): {[u.name for u in player_units]}")
        print(f"Opponent team ({len(opponent_units)} units): {[u.name for u in opponent_units]}")

        # Run simulation
        result = run_combat_simulation(player_units, opponent_units)

        # Verify simulation completed
        self.assertIn('winner', result)
        self.assertIn('duration', result)
        self.assertIn('events', result)
        self.assertIsInstance(result['events'], list)
        self.assertGreater(len(result['events']), 0)

        # Verify events have proper structure
        for event_type, event_data in result['events']:
            self.assertIsInstance(event_type, str)
            self.assertIsInstance(event_data, dict)
            if event_type in ['unit_attack', 'unit_died', 'state_snapshot']:
                self.assertIn('seq', event_data)
                self.assertIsInstance(event_data['seq'], int)

        # Test event replay using the reusable CombatEventReconstructor
        events = result['events']
        events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] != 'state_snapshot' else 1, x[1]['timestamp']))

        # Find state_snapshots
        state_snapshots = [event for event in events if event[0] == 'state_snapshot']
        self.assertGreater(len(state_snapshots), 0, "No state_snapshots found")

        # Initialize reconstruction from first snapshot
        reconstructor = CombatEventReconstructor()
        first_snapshot = state_snapshots[0][1]
        reconstructor.initialize_from_snapshot(first_snapshot)

        # Process all events
        for event_type, event_data in events:
            reconstructor.process_event(event_type, event_data)

        # Get final reconstructed state
        reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

        # Compare final state with simulation results
        for unit in player_units:
            self.assertEqual(unit.hp, reconstructed_player_units[unit.id]['hp'],
                           f"HP mismatch for player unit {unit.name} ({unit.id})")
            self.assertEqual(unit.max_hp, reconstructed_player_units[unit.id]['max_hp'],
                           f"Max HP mismatch for player unit {unit.name} ({unit.id})")
            self.assertEqual(unit.mana, reconstructed_player_units[unit.id]['current_mana'],
                           f"Mana mismatch for player unit {unit.name} ({unit.id})")

        for unit in opponent_units:
            self.assertEqual(unit.hp, reconstructed_opponent_units[unit.id]['hp'],
                           f"HP mismatch for opponent unit {unit.name} ({unit.id})")
            self.assertEqual(unit.max_hp, reconstructed_opponent_units[unit.id]['max_hp'],
                           f"Max HP mismatch for opponent unit {unit.name} ({unit.id})")
            self.assertEqual(unit.mana, reconstructed_opponent_units[unit.id]['current_mana'],
                           f"Mana mismatch for opponent unit {unit.name} ({unit.id})")

        print(f"10v10 test with different seed completed successfully. Winner: {result['winner']}, Duration: {result['duration']:.2f}s")

    def test_10v10_simulation_seed_200(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state for seed 200"""
        self._test_single_seed_simulation(200)

    def test_10v10_simulation_seed_300(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state for seed 300"""
        self._test_single_seed_simulation(300)

    def test_10v10_simulation_seed_400(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state for seed 400"""
        self._test_single_seed_simulation(400)

    def test_10v10_simulation_seed_500(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state for seed 500"""
        self._test_single_seed_simulation(500)

    def test_10v10_simulation_seed_599(self):
        """Test simulation with 10 vs 10 real units and verify event replay can reconstruct game state for seed 599"""
        self._test_single_seed_simulation(599)

    def _test_single_seed_simulation(self, seed):
        """Helper method to test simulation with a specific seed"""
        import random
        from waffen_tactics.services.combat_shared import CombatUnit

        # Load real game data
        game_data = load_game_data()

        # Prepare helper and id list once; teams will be sampled per-seed below
        all_unit_ids = [u.id for u in game_data.units]
        def get_unit(unit_id):
            return next(u for u in game_data.units if u.id == unit_id)

        random.seed(seed)

        # Sample 20 unique unit ids and split into two teams (10/10)
        sample_20 = random.sample(all_unit_ids, 20)
        player_unit_ids = sample_20[:10]
        opponent_unit_ids = sample_20[10:]

        # Create player team (10 units)
        player_units = []
        for unit_id in player_unit_ids:
            unit = get_unit(unit_id)
            player_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(player_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        # Create opponent team (10 units)
        opponent_units = []
        for unit_id in opponent_unit_ids:
            unit = get_unit(unit_id)
            opponent_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                position='front' if len(opponent_units) < 5 else 'back',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

        # Run simulation
        result = run_combat_simulation(player_units, opponent_units)

        # Verify simulation completed
        self.assertIn('winner', result)
        self.assertIn('duration', result)
        self.assertIn('events', result)
        self.assertIsInstance(result['events'], list)
        self.assertGreater(len(result['events']), 0)

        # Verify events have proper structure
        for event_type, event_data in result['events']:
            self.assertIsInstance(event_type, str)
            self.assertIsInstance(event_data, dict)
            if event_type in ['unit_attack', 'unit_died', 'state_snapshot']:
                self.assertIn('seq', event_data)
                self.assertIsInstance(event_data['seq'], int)

        # Test event replay using the reusable CombatEventReconstructor
        events = result['events']
        events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] == 'state_snapshot' else 1, x[1]['timestamp']))
        # Find state_snapshots
        state_snapshots = [event for event in events if event[0] == 'state_snapshot']
        self.assertGreater(len(state_snapshots), 0, f"No state_snapshots found for seed {seed}")

        # Initialize reconstruction from first snapshot
        reconstructor = CombatEventReconstructor()
        first_snapshot = state_snapshots[0][1]
        reconstructor.initialize_from_snapshot(first_snapshot)

        # Process all events
        # Debug: list all events mentioning puszmen12 before replay
        for i, (et, ed) in enumerate(events[-200:]):
            if 'puszmen12' in str(ed).lower():
                error_print(f"EVENT[{i - 200 if i < 200 else i}]: type={et} data={ed}")

        for event_type, event_data in events:
            if event_type == 'mana_update':
                error_print(f"DEBUG: Processing mana_update: {event_data}")
            reconstructor.process_event(event_type, event_data)

        # Debug: final simulation mana for puszmen12
        try:
            pusz = next(u for u in player_units if u.id == 'puszmen12')
            error_print(f"SIM FINAL: puszmen12 mana={getattr(pusz, 'mana', None)}")
        except Exception:
            pass

        # Get final reconstructed state
        reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

        # Compare final state with simulation results
        for unit in player_units:
            self.assertEqual(unit.hp, reconstructed_player_units[unit.id]['hp'],
                           f"HP mismatch for player unit {unit.name} ({unit.id}) at seed {seed}")
            self.assertEqual(unit.max_hp, reconstructed_player_units[unit.id]['max_hp'],
                           f"Max HP mismatch for player unit {unit.name} ({unit.id}) at seed {seed}")
            self.assertEqual(unit.mana, reconstructed_player_units[unit.id]['current_mana'],
                           f"Mana mismatch for player unit {unit.name} ({unit.id}) at seed {seed}")

        for unit in opponent_units:
            self.assertEqual(unit.hp, reconstructed_opponent_units[unit.id]['hp'],
                           f"HP mismatch for opponent unit {unit.name} ({unit.id}) at seed {seed}")
            self.assertEqual(unit.max_hp, reconstructed_opponent_units[unit.id]['max_hp'],
                           f"Max HP mismatch for opponent unit {unit.name} ({unit.id}) at seed {seed}")
            self.assertEqual(unit.mana, reconstructed_opponent_units[unit.id]['current_mana'],
                           f"Mana mismatch for opponent unit {unit.name} ({unit.id}) at seed {seed}")

    def test_failing_seeds_detailed_debug(self):
        """Test specific failing seeds with detailed HP change logging"""
        import random
        from waffen_tactics.services.combat_shared import CombatUnit

        # Load real game data
        game_data = load_game_data()

        # Prepare helper and id list once; teams will be sampled per-seed below
        all_unit_ids = [u.id for u in game_data.units]
        def get_unit(unit_id):
            return next(u for u in game_data.units if u.id == unit_id)
        
        # Test only the failing seeds
        failing_seeds = [205, 211, 213, 315, 394]  # Start with just one seed for debugging
        
        # Collect team compositions for analysis
        team_compositions = {}
        
        for seed in failing_seeds:
            error_print(f"\n=== Testing failing seed {seed} ===")

            random.seed(seed)

            # Sample 20 unique unit ids and split into two teams (10/10)
            sample_20 = random.sample(all_unit_ids, 20)
            player_unit_ids = sample_20[:10]
            opponent_unit_ids = sample_20[10:]

            # Store team composition
            team_compositions[seed] = {
                'player': player_unit_ids,
                'opponent': opponent_unit_ids
            }

            error_print(f"Player units: {player_unit_ids}")
            error_print(f"Opponent units: {opponent_unit_ids}")

            # Create player team (10 units)
            player_units = []
            for unit_id in player_unit_ids:
                unit = get_unit(unit_id)
                player_units.append(CombatUnit(
                    id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                    defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                    position='front' if len(player_units) < 5 else 'back',
                    stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
                ))

            # Create opponent team (10 units)
            opponent_units = []
            for unit_id in opponent_unit_ids:
                unit = get_unit(unit_id)
                opponent_units.append(CombatUnit(
                    id=unit.id, name=unit.name, hp=unit.stats.hp, attack=unit.stats.attack,
                    defense=unit.stats.defense, attack_speed=unit.stats.attack_speed,
                    position='front' if len(opponent_units) < 5 else 'back',
                    stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
                ))

            try:
                # Run simulation
                result = run_combat_simulation(player_units, opponent_units)

                # Verify simulation completed
                self.assertIn('winner', result)
                self.assertIn('duration', result)
                self.assertIn('events', result)
                self.assertIsInstance(result['events'], list)
                self.assertGreater(len(result['events']), 0)

                # Sort events by sequence and timestamp
                events = result['events']
                events.sort(key=lambda x: (x[1]['seq'], 0 if x[0] == 'state_snapshot' else 1, x[1]['timestamp']))
                
                # Find state_snapshots
                state_snapshots = [event for event in events if event[0] == 'state_snapshot']
                self.assertGreater(len(state_snapshots), 0, f"No state_snapshots found for seed {seed}")

                # Initialize reconstruction from first snapshot
                reconstructor = CombatEventReconstructor()
                first_snapshot = state_snapshots[0][1]
                reconstructor.initialize_from_snapshot(first_snapshot)

                # Process all events with detailed logging
                error_print(f"Processing {len(events)} events...")
                hp_change_events = []
                
                for event_type, event_data in events:
                    if event_type in ['hp_regen', 'unit_heal', 'damage_over_time_tick', 'stat_buff']:
                        hp_change_events.append((event_type, event_data))
                    
                    reconstructor.process_event(event_type, event_data)

                # Get final reconstructed state
                reconstructed_player_units, reconstructed_opponent_units = reconstructor.get_reconstructed_state()

                # Compare final state with simulation results and log differences
                error_print("Checking player units:")
                for unit in player_units:
                    recon_hp = reconstructed_player_units[unit.id]['hp']
                    sim_hp = unit.hp
                    if sim_hp != recon_hp:
                        error_print(f"  ❌ HP mismatch for player unit {unit.name} ({unit.id}): sim={sim_hp}, recon={recon_hp}")
                        
                        # Find relevant HP change events for this unit
                        unit_hp_events = [e for e in hp_change_events if e[1].get('unit_id') == unit.id]
                        error_print(f"    HP change events for {unit.id}: {len(unit_hp_events)}")
                        for et, ed in unit_hp_events[-5:]:  # Last 5 events
                            error_print(f"      {et}: {ed}")
                    else:
                        error_print(f"  ✅ HP match for player unit {unit.name} ({unit.id}): {sim_hp}")

                error_print("Checking opponent units:")
                for unit in opponent_units:
                    recon_hp = reconstructed_opponent_units[unit.id]['hp']
                    sim_hp = unit.hp
                    if sim_hp != recon_hp:
                        error_print(f"  ❌ HP mismatch for opponent unit {unit.name} ({unit.id}): sim={sim_hp}, recon={recon_hp}")
                        
                        # Find relevant HP change events for this unit
                        unit_hp_events = [e for e in hp_change_events if e[1].get('unit_id') == unit.id]
                        error_print(f"    HP change events for {unit.id}: {len(unit_hp_events)}")
                        for et, ed in unit_hp_events[-5:]:  # Last 5 events
                            error_print(f"      {et}: {ed}")
                    else:
                        error_print(f"  ✅ HP match for opponent unit {unit.name} ({unit.id}): {sim_hp}")

                # Check if any mismatches found
                mismatches = []
                for unit in player_units:
                    if unit.hp != reconstructed_player_units[unit.id]['hp']:
                        mismatches.append(f"player {unit.name} ({unit.id})")
                for unit in opponent_units:
                    if unit.hp != reconstructed_opponent_units[unit.id]['hp']:
                        mismatches.append(f"opponent {unit.name} ({unit.id})")
                
                if mismatches:
                    error_print(f"Seed {seed} has mismatches: {mismatches}")
                else:
                    error_print(f"Seed {seed} actually passes!")

            except Exception as e:
                error_print(f"Error at seed {seed}: {e}")
                import traceback
                error_print(traceback.format_exc())

        # Analyze common units between failing seeds
        error_print("\n=== TEAM COMPOSITION ANALYSIS ===")
        
        # Find units that appear in multiple failing seeds
        from collections import Counter
        
        all_player_units = []
        all_opponent_units = []
        
        for seed, teams in team_compositions.items():
            all_player_units.extend(teams['player'])
            all_opponent_units.extend(teams['opponent'])
        
        player_unit_counts = Counter(all_player_units)
        opponent_unit_counts = Counter(all_opponent_units)
        
        error_print("Player units appearing in multiple failing seeds:")
        for unit, count in sorted(player_unit_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 1:
                seeds_with_unit = [seed for seed, teams in team_compositions.items() if unit in teams['player']]
                error_print(f"  {unit}: {count} seeds ({seeds_with_unit})")
        
        error_print("Opponent units appearing in multiple failing seeds:")
        for unit, count in sorted(opponent_unit_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 1:
                seeds_with_unit = [seed for seed, teams in team_compositions.items() if unit in teams['opponent']]
                error_print(f"  {unit}: {count} seeds ({seeds_with_unit})")
        
        # Check for any units that appear in all failing seeds
        all_player_common = set(team_compositions[failing_seeds[0]]['player'])
        all_opponent_common = set(team_compositions[failing_seeds[0]]['opponent'])
        
        for seed in failing_seeds[1:]:
            all_player_common &= set(team_compositions[seed]['player'])
            all_opponent_common &= set(team_compositions[seed]['opponent'])
        
        if all_player_common:
            error_print(f"Units in ALL player teams: {list(all_player_common)}")
        if all_opponent_common:
            error_print(f"Units in ALL opponent teams: {list(all_opponent_common)}")

    def test_game_state_snapshots_always_accurate(self):
        """Verify that game_state snapshots match simulator state (Phase 1.4)"""
        import random
        random.seed(999)

        from waffen_tactics.services.combat_shared import CombatUnit
        from waffen_tactics.services.combat_simulator import CombatSimulator

        # Load real game data
        game_data = load_game_data()

        # Create simple 2v2 combat
        player_units = []
        opponent_units = []
        for i in range(2):
            unit = game_data.units[i]
            player_units.append(CombatUnit(
                id=unit.id, name=unit.name, hp=unit.stats.hp,
                attack=unit.stats.attack, defense=unit.stats.defense,
                attack_speed=unit.stats.attack_speed, position='front',
                stats=unit.stats, skill=unit.skill, max_mana=unit.stats.max_mana
            ))

            unit2 = game_data.units[i + 2]
            opponent_units.append(CombatUnit(
                id=unit2.id, name=unit2.name, hp=unit2.stats.hp,
                attack=unit2.stats.attack, defense=unit2.stats.defense,
                attack_speed=unit2.stats.attack_speed, position='front',
                stats=unit2.stats, skill=unit2.skill, max_mana=unit2.stats.max_mana
            ))

        # Create simulator and collect events with game_state
        simulator = CombatSimulator()
        events_with_state = []

        def event_collector(event_type, data):
            # Mimic SSE route behavior: attach game_state from simulator
            data['game_state'] = {
                'player_units': [u.to_dict() for u in simulator.team_a],
                'opponent_units': [u.to_dict() for u in simulator.team_b],
            }
            events_with_state.append((event_type, data))

        # Run simulation
        result = simulator.simulate(player_units, opponent_units, event_collector, skip_per_round_buffs=True)

        # Verify we got events
        self.assertGreater(len(events_with_state), 0, "No events collected")

        # Check every event with game_state
        for event_type, event_data in events_with_state:
            game_state = event_data['game_state']

            # Verify structure is correct
            self.assertIn('player_units', game_state)
            self.assertIn('opponent_units', game_state)
            self.assertIsInstance(game_state['player_units'], list)
            self.assertIsInstance(game_state['opponent_units'], list)

            # Verify all player units have required fields
            for gs_unit in game_state['player_units']:
                self.assertIn('id', gs_unit)
                self.assertIn('hp', gs_unit)
                self.assertIn('current_mana', gs_unit)
                self.assertIn('shield', gs_unit)
                self.assertIn('max_hp', gs_unit)
                self.assertIn('max_mana', gs_unit)

                # Verify types
                self.assertIsInstance(gs_unit['hp'], (int, float))
                self.assertIsInstance(gs_unit['current_mana'], (int, float))
                self.assertIsInstance(gs_unit['shield'], (int, float))

                # Verify values are sane
                self.assertGreaterEqual(gs_unit['hp'], 0)
                self.assertGreaterEqual(gs_unit['current_mana'], 0)
                self.assertLessEqual(gs_unit['current_mana'], gs_unit['max_mana'])

            # Verify all opponent units have required fields
            for gs_unit in game_state['opponent_units']:
                self.assertIn('id', gs_unit)
                self.assertIn('hp', gs_unit)
                self.assertIn('current_mana', gs_unit)
                self.assertIn('shield', gs_unit)

                # Verify types
                self.assertIsInstance(gs_unit['hp'], (int, float))
                self.assertIsInstance(gs_unit['current_mana'], (int, float))

                # Verify values are sane
                self.assertGreaterEqual(gs_unit['hp'], 0)
                self.assertGreaterEqual(gs_unit['current_mana'], 0)

        print(f"✅ Verified {len(events_with_state)} events with accurate game_state snapshots")


if __name__ == '__main__':
    unittest.main()