"""
Tests for Game State Utils
"""
import unittest
from unittest.mock import MagicMock, patch
from waffen_tactics.models.player_state import PlayerState, UnitInstance
from routes.game_state_utils import enrich_player_state


class TestGameStateUtils(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = 123

        # Create mock player
        self.mock_player = MagicMock(spec=PlayerState)
        self.mock_player.user_id = self.user_id
        self.mock_player.hp = 100
        self.mock_player.board = []
        self.mock_player.bench = []
        self.mock_player.max_board_size = 7
        self.mock_player.wins = 5
        self.mock_player.losses = 3
        self.mock_player.level = 1
        self.mock_player.xp = 0
        self.mock_player.gold = 10
        self.mock_player.streak = 0
        self.mock_player.round_number = 1
        self.mock_player.locked_shop = False
        self.mock_player.xp_to_next_level = 2
        self.mock_player.last_shop = []
        self.mock_player.last_shop_detailed = []
        self.mock_player.to_dict.return_value = {
            "user_id": self.user_id,
            "board": [],
            "bench": []
        }

        # Create mock unit
        self.mock_unit = MagicMock()
        self.mock_unit.id = "unit_001"
        self.mock_unit.name = "Test Unit"
        self.mock_unit.cost = 1
        self.mock_unit.factions = ["TestFaction"]
        self.mock_unit.classes = ["Normik"]  # Has Normik class for synergy testing
        self.mock_unit.stats = MagicMock()
        self.mock_unit.stats.hp = 100
        self.mock_unit.stats.attack = 20
        self.mock_unit.stats.defense = 5
        self.mock_unit.stats.attack_speed = 0.8
        self.mock_unit.stats.max_mana = 100
        self.mock_unit.stats.mana_regen = 5

        # Create mock unit instance
        self.mock_unit_instance = MagicMock(spec=UnitInstance)
        self.mock_unit_instance.unit_id = "unit_001"
        self.mock_unit_instance.instance_id = "inst_001"
        self.mock_unit_instance.star_level = 1
        self.mock_unit_instance.position = "front"
        self.mock_unit_instance.persistent_buffs = {}

    @patch('routes.game_state_utils.GameManager')
    def test_enrich_player_state_hp_calculation_with_synergies_and_persistent_buffs(self, mock_game_manager_cls):
        """Test HP calculation in enrich_player_state with synergies and persistent buffs"""
        # Setup mocks
        mock_game_manager = MagicMock()
        mock_game_manager_cls.return_value = mock_game_manager
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.data.traits = [
            {
                "name": "Normik",
                "type": "class",
                "thresholds": [2, 4, 5],
                "effects": [
                    {"type": "stat_buff", "stat": "hp", "value": 20, "is_percentage": True},
                    {"type": "stat_buff", "stat": "hp", "value": 40, "is_percentage": True},
                    {"type": "stat_buff", "stat": "hp", "value": 60, "is_percentage": True}
                ]
            }
        ]
        
        # Mock synergies - 2 Normik units, tier 1 (+20% HP)
        mock_game_manager.get_board_synergies.return_value = {"Normik": (2, 1)}
        
        # Synergy engine mocks
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 120, 'attack': 20, 'defense': 5, 'attack_speed': 0.8  # 100 * 1.2 = 120
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 120, 'attack': 20, 'defense': 5, 'attack_speed': 0.8, 'max_mana': 100, 'current_mana': 0
        }
        
        # Create unit instance with persistent HP buff
        self.mock_unit_instance.persistent_buffs = {'hp': 50}
        self.mock_player.board = [self.mock_unit_instance]
        self.mock_player.to_dict.return_value = {
            "user_id": self.user_id,
            "board": [{"instance_id": "inst_001", "unit_id": "unit_001", "star_level": 1, "position": "front"}],
            "bench": []
        }

        # Execute
        result = enrich_player_state(self.mock_player)

        # Assert
        board_units = result.get('board', [])
        self.assertEqual(len(board_units), 1)
        
        unit_data = board_units[0]
        buffed_stats = unit_data.get('buffed_stats', {})
        
        # Expected: base 100 -> synergies +20% = 120 -> persistent +50 = 170
        expected_hp = 120 + 50
        self.assertEqual(buffed_stats.get('hp'), expected_hp)
        
        # Base stats should be just scaled (no synergies, no persistent)
        base_stats = unit_data.get('base_stats', {})
        expected_base_hp = 100  # 100 * (1.6^(1-1)) = 100
        self.assertEqual(base_stats.get('hp'), expected_base_hp)

    @patch('routes.game_state_utils.GameManager')
    def test_enrich_player_state_hp_calculation_order_verification(self, mock_game_manager_cls):
        """Test that HP buffs are applied in correct order in enrich_player_state: base -> synergies -> persistent"""
        # Setup mocks
        mock_game_manager = MagicMock()
        mock_game_manager_cls.return_value = mock_game_manager
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.data.traits = [
            {
                "name": "Normik",
                "type": "class",
                "thresholds": [2, 4, 5],
                "effects": [
                    {"type": "stat_buff", "stat": "hp", "value": 20, "is_percentage": True},
                    {"type": "stat_buff", "stat": "hp", "value": 40, "is_percentage": True},
                    {"type": "stat_buff", "stat": "hp", "value": 60, "is_percentage": True}
                ]
            }
        ]
        
        # Mock synergies - 4 Normik units, tier 2 (+40% HP)
        mock_game_manager.get_board_synergies.return_value = {"Normik": (4, 2)}
        
        # Synergy engine mocks
        mock_game_manager.synergy_engine.apply_stat_buffs.return_value = {
            'hp': 140, 'attack': 20, 'defense': 5, 'attack_speed': 0.8  # 100 * 1.4 = 140
        }
        mock_game_manager.synergy_engine.apply_dynamic_effects.return_value = {
            'hp': 140, 'attack': 20, 'defense': 5, 'attack_speed': 0.8, 'max_mana': 100, 'current_mana': 0
        }
        
        # Create unit instance with persistent HP buff
        self.mock_unit_instance.persistent_buffs = {'hp': 100}
        self.mock_player.board = [self.mock_unit_instance]
        self.mock_player.to_dict.return_value = {
            "user_id": self.user_id,
            "board": [{"instance_id": "inst_001", "unit_id": "unit_001", "star_level": 1, "position": "front"}],
            "bench": []
        }

        # Execute
        result = enrich_player_state(self.mock_player)

        # Assert
        board_units = result.get('board', [])
        unit_data = board_units[0]
        buffed_stats = unit_data.get('buffed_stats', {})
        
        # Expected: base 100 -> synergies +40% = 140 -> persistent +100 = 240
        expected_hp = 140 + 100
        self.assertEqual(buffed_stats.get('hp'), expected_hp)

    @patch('routes.game_state_utils.GameManager')
    def test_enrich_player_state_bench_units_no_synergies_but_persistent_buffs(self, mock_game_manager_cls):
        """Test that bench units get persistent buffs but no synergies"""
        # Setup mocks
        mock_game_manager = MagicMock()
        mock_game_manager_cls.return_value = mock_game_manager
        mock_game_manager.data.units = [self.mock_unit]
        mock_game_manager.data.traits = []
        
        # No synergies for bench
        mock_game_manager.get_board_synergies.return_value = {}
        
        # Create unit instance with persistent HP buff on bench
        self.mock_unit_instance.persistent_buffs = {'hp': 75}
        self.mock_player.bench = [self.mock_unit_instance]
        self.mock_player.to_dict.return_value = {
            "user_id": self.user_id,
            "board": [],
            "bench": [{"instance_id": "inst_001", "unit_id": "unit_001", "star_level": 1, "position": "front"}]
        }

        # Execute
        result = enrich_player_state(self.mock_player)

        # Assert
        bench_units = result.get('bench', [])
        self.assertEqual(len(bench_units), 1)
        
        unit_data = bench_units[0]
        buffed_stats = unit_data.get('buffed_stats', {})
        base_stats = unit_data.get('base_stats', {})
        
        # Bench: base HP + persistent buffs (no synergies)
        expected_base_hp = 100  # 100 * (1.6^(1-1)) = 100
        expected_buffed_hp = 100 + 75  # base + persistent
        
        self.assertEqual(base_stats.get('hp'), expected_base_hp)
        self.assertEqual(buffed_stats.get('hp'), expected_buffed_hp)


if __name__ == '__main__':
    unittest.main()