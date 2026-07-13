"""
Tests for the deprecated persistent-buff helper.

The helper is intentionally a no-op in the current ruleset. These tests now
assert that it leaves unit state untouched.
"""
import unittest
from unittest.mock import Mock, MagicMock
from services.combat_service import _apply_persistent_buffs_from_kills


class TestPersistentBuffsOnEnemyDeath(unittest.TestCase):
    """Test cases for the deprecated no-op persistent buff helper"""

    def test_persistent_buff_on_enemy_death_is_noop(self):
        """The deprecated helper should not mutate persistent buffs."""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'TestTrait',
            'target': 'trait',
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'attack',
                    'value': 5,
                    'is_percentage': False,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'test_unit'
        mock_unit.factions = ['TestTrait']
        mock_unit.classes = []
        mock_game_manager.data.units = [mock_unit]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance = Mock()
        mock_unit_instance.instance_id = 'instance_1'
        mock_unit_instance.unit_id = 'test_unit'
        mock_unit_instance.persistent_buffs = {}
        mock_player.board = [mock_unit_instance]

        # Mock collected stats - unit collected 30 defense total
        collected_stats_maps = {
            'instance_1': {
                'kills': 2,
                'defense': 30
            }
        }

        # Mock synergies - player has TestTrait tier 1
        player_synergies = {
            'TestTrait': (1, 1)
        }

        # Call the method that applies persistent buffs
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance.persistent_buffs, {})

    def test_persistent_buff_percentage_based_on_enemy_death_is_noop(self):
        """Percentage-based legacy buffs should also be ignored."""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'PercentTrait',
            'target': 'trait',
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'defense',
                    'value': 25,  # 25%
                    'is_percentage': True,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'percent_unit'
        mock_unit.factions = ['PercentTrait']
        mock_unit.classes = []
        mock_game_manager.data.units = [mock_unit]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance = Mock()
        mock_unit_instance.instance_id = 'instance_2'
        mock_unit_instance.unit_id = 'percent_unit'
        mock_unit_instance.persistent_buffs = {'defense': 5}  # Already has 5 defense
        mock_player.board = [mock_unit_instance]

        # Mock collected stats - collected 40 defense total
        collected_stats_maps = {
            'instance_2': {
                'kills': 1,
                'defense': 40
            }
        }

        # Mock synergies
        player_synergies = {
            'PercentTrait': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance.persistent_buffs, {'defense': 5})

    def test_persistent_buff_team_target_on_enemy_death_is_noop(self):
        """Team-targeted legacy buffs should remain untouched."""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'TeamTrait',
            'target': 'team',  # Applies to entire team
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'hp',
                    'value': 3,
                    'is_percentage': False,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data (not needed for team target)
        mock_game_manager.data.units = []

        # Mock player with multiple board units
        mock_player = Mock()
        mock_unit_instance1 = Mock()
        mock_unit_instance1.instance_id = 'instance_1'
        mock_unit_instance1.unit_id = 'unit1'
        mock_unit_instance1.persistent_buffs = {}

        mock_unit_instance2 = Mock()
        mock_unit_instance2.instance_id = 'instance_2'
        mock_unit_instance2.unit_id = 'unit2'
        mock_unit_instance2.persistent_buffs = {}

        mock_player.board = [mock_unit_instance1, mock_unit_instance2]

        # Mock collected stats
        collected_stats_maps = {
            'instance_1': {'kills': 2, 'defense': 20},
            'instance_2': {'kills': 1, 'defense': 15}
        }

        # Mock synergies
        player_synergies = {
            'TeamTrait': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance1.persistent_buffs, {})
        self.assertEqual(mock_unit_instance2.persistent_buffs, {})

    def test_persistent_buff_trait_target_on_enemy_death_is_noop(self):
        """Trait-targeted legacy buffs should not be applied either."""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'TraitOnly',
            'target': 'trait',  # Only units with this trait
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'attack_speed',
                    'value': 0.1,
                    'is_percentage': False,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit_trait = Mock()
        mock_unit_trait.id = 'trait_unit'
        mock_unit_trait.factions = ['TraitOnly']
        mock_unit_trait.classes = []

        mock_unit_no_trait = Mock()
        mock_unit_no_trait.id = 'no_trait_unit'
        mock_unit_no_trait.factions = []
        mock_unit_no_trait.classes = []

        mock_game_manager.data.units = [mock_unit_trait, mock_unit_no_trait]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance_trait = Mock()
        mock_unit_instance_trait.instance_id = 'instance_trait'
        mock_unit_instance_trait.unit_id = 'trait_unit'
        mock_unit_instance_trait.persistent_buffs = {}

        mock_unit_instance_no_trait = Mock()
        mock_unit_instance_no_trait.instance_id = 'instance_no_trait'
        mock_unit_instance_no_trait.unit_id = 'no_trait_unit'
        mock_unit_instance_no_trait.persistent_buffs = {}

        mock_player.board = [mock_unit_instance_trait, mock_unit_instance_no_trait]

        # Mock collected stats
        collected_stats_maps = {
            'instance_trait': {'kills': 1, 'defense': 25},
            'instance_no_trait': {'kills': 1, 'defense': 25}
        }

        # Mock synergies
        player_synergies = {
            'TraitOnly': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance_trait.persistent_buffs, {})
        self.assertEqual(mock_unit_instance_no_trait.persistent_buffs, {})

    def test_persistent_buff_zero_increment_not_applied(self):
        """Test that zero increment persistent buffs are not applied"""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'ZeroTrait',
            'target': 'trait',
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'attack',
                    'value': 5,
                    'is_percentage': False,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'zero_unit'
        mock_unit.factions = ['ZeroTrait']
        mock_unit.classes = []
        mock_game_manager.data.units = [mock_unit]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance = Mock()
        mock_unit_instance.instance_id = 'instance_zero'
        mock_unit_instance.unit_id = 'zero_unit'
        mock_unit_instance.persistent_buffs = {}
        mock_player.board = [mock_unit_instance]

        # Mock collected stats - no kills, so increment should be 0
        collected_stats_maps = {
            'instance_zero': {
                'kills': 0,
                'defense': 0
            }
        }

        # Mock synergies
        player_synergies = {
            'ZeroTrait': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        # No buff should be applied since increment is 0
        self.assertEqual(len(mock_unit_instance.persistent_buffs), 0)

    def test_persistent_buff_on_max_mana_stat_is_noop(self):
        """Max mana legacy buffs should not be applied."""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'ManaTrait',
            'target': 'trait',
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'max_mana',
                    'value': 10,
                    'is_percentage': False,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'mana_unit'
        mock_unit.factions = ['ManaTrait']
        mock_unit.classes = []
        mock_game_manager.data.units = [mock_unit]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance = Mock()
        mock_unit_instance.instance_id = 'instance_mana'
        mock_unit_instance.unit_id = 'mana_unit'
        mock_unit_instance.persistent_buffs = {}
        mock_player.board = [mock_unit_instance]

        # Mock collected stats
        collected_stats_maps = {
            'instance_mana': {
                'kills': 3,
                'defense': 50
            }
        }

        # Mock synergies
        player_synergies = {
            'ManaTrait': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance.persistent_buffs, {})

    def test_persistent_buff_percentage_on_hp_stat_is_noop(self):
        """HP legacy buffs should not be applied."""
        # Mock game manager with trait data
        mock_trait = {
            'name': 'HpPercentTrait',
            'target': 'trait',
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'hp',
                    'value': 50,  # 50%
                    'is_percentage': True,
                    'collect_stat': 'defense'
                }]
            }]
        }
        mock_game_manager = Mock()
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'hp_percent_unit'
        mock_unit.factions = ['HpPercentTrait']
        mock_unit.classes = []
        mock_game_manager.data.units = [mock_unit]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance = Mock()
        mock_unit_instance.instance_id = 'instance_hp_percent'
        mock_unit_instance.unit_id = 'hp_percent_unit'
        mock_unit_instance.persistent_buffs = {'hp': 20}  # Already has 20 hp buff
        mock_player.board = [mock_unit_instance]

        # Mock collected stats - collected 100 defense total
        collected_stats_maps = {
            'instance_hp_percent': {
                'kills': 1,
                'defense': 100
            }
        }

        # Mock synergies
        player_synergies = {
            'HpPercentTrait': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance.persistent_buffs, {'hp': 20})

    def test_persistent_buff_flat_buff_different_collect_stat_is_noop(self):
        """Alternative collect stats should also be ignored in the no-op helper."""
        # Mock game manager with trait data
        mock_game_manager = Mock()
        mock_trait = {
            'name': 'AttackCollectTrait',
            'target': 'trait',
            'effects': [{
                'type': 'on_enemy_death',
                'actions': [{
                    'type': 'kill_buff',
                    'stat': 'defense',
                    'value': 2,  # +2 defense per collected attack
                    'is_percentage': False,
                    'collect_stat': 'attack'  # Collect attack instead of kills
                }]
            }]
        }
        mock_game_manager.data.traits = [mock_trait]

        # Mock unit data
        mock_unit = Mock()
        mock_unit.id = 'attack_collect_unit'
        mock_unit.factions = ['AttackCollectTrait']
        mock_unit.classes = []
        mock_game_manager.data.units = [mock_unit]

        # Mock player with board units
        mock_player = Mock()
        mock_unit_instance = Mock()
        mock_unit_instance.instance_id = 'instance_attack_collect'
        mock_unit_instance.unit_id = 'attack_collect_unit'
        mock_unit_instance.persistent_buffs = {}
        mock_player.board = [mock_unit_instance]

        # Mock collected stats - collected 40 attack total
        collected_stats_maps = {
            'instance_attack_collect': {
                'kills': 1,
                'attack': 40
            }
        }

        # Mock synergies
        player_synergies = {
            'AttackCollectTrait': (1, 1)
        }

        # Call the method
        _apply_persistent_buffs_from_kills(
            mock_player, player_synergies, collected_stats_maps, mock_game_manager
        )

        self.assertEqual(mock_unit_instance.persistent_buffs, {})


if __name__ == '__main__':
    unittest.main()
