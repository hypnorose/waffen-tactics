"""
Tests for EffectProcessor coordination class
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from waffen_tactics.services.effect_processor import EffectProcessor


class TestEffectProcessor(unittest.TestCase):
    """Test cases for EffectProcessor class"""

    def setUp(self):
        """Set up test fixtures"""
        self.processor = EffectProcessor()

        # Create mock units
        self.source_unit = Mock()
        self.source_unit.id = "source_1"
        self.source_unit.name = "SourceUnit"
        self.source_unit.factions = ['human']
        self.source_unit.classes = ['warrior']

        self.recipient_unit = Mock()
        self.recipient_unit.id = "recipient_1"
        self.recipient_unit.name = "RecipientUnit"
        self.recipient_unit.factions = ['human']
        self.recipient_unit.classes = ['warrior']
        self.recipient_unit.hp = 100

        self.attacking_team = [self.source_unit]
        self.defending_team = [self.recipient_unit]
        self.attacking_hp = [100]
        self.defending_hp = [100]

    def test_init_creates_utility_instances(self):
        """Test that EffectProcessor initializes utility classes"""
        self.assertIsNotNone(self.processor.stat_calculator)
        self.assertIsNotNone(self.processor.recipient_resolver)
        self.assertIsNotNone(self.processor.buff_handlers)
        self.assertIn('attack', self.processor.buff_handlers)
        self.assertIn('defense', self.processor.buff_handlers)

    @patch('waffen_tactics.services.effect_processor.EffectProcessor._process_kill_buff')
    def test_process_effect_kill_buff(self, mock_process_kill_buff):
        """Test processing kill_buff action"""
        effect = {'action': 'kill_buff', 'stat_type': 'attack', 'value': 10}
        mock_process_kill_buff.return_value = {'processed': True, 'changes': {}}

        result = self.processor.process_effect(
            effect, self.source_unit, self.attacking_team,
            self.defending_team, self.attacking_hp, self.defending_hp, 'team_a'
        )

        mock_process_kill_buff.assert_called_once()
        self.assertTrue(result['processed'])

    @patch('waffen_tactics.services.effect_processor.EffectProcessor._process_collect_stat')
    def test_process_effect_collect_stat(self, mock_process_collect_stat):
        """Test processing collect_stat action"""
        effect = {'action': 'collect_stat', 'stat_type': 'defense'}
        mock_process_collect_stat.return_value = {'processed': True, 'changes': {}}

        result = self.processor.process_effect(
            effect, self.source_unit, self.attacking_team,
            self.defending_team, self.attacking_hp, self.defending_hp, 'team_a'
        )

        mock_process_collect_stat.assert_called_once()
        self.assertTrue(result['processed'])

    def test_process_effect_unknown_action(self):
        """Test processing unknown action"""
        effect = {'action': 'unknown_action'}

        result = self.processor.process_effect(
            effect, self.source_unit, self.attacking_team,
            self.defending_team, self.attacking_hp, self.defending_hp, 'team_a'
        )

        self.assertFalse(result['processed'])
        self.assertIn('Unknown action: unknown_action', result['errors'])

    def test_process_effect_exception_handling(self):
        """Test exception handling in process_effect"""
        effect = {'action': 'kill_buff'}

        # Mock recipient_resolver to raise exception
        with patch.object(self.processor.recipient_resolver, 'find_recipients',
                         side_effect=Exception("Test error")):
            result = self.processor.process_effect(
                effect, self.source_unit, self.attacking_team,
                self.defending_team, self.attacking_hp, self.defending_hp, 'team_a'
            )

            self.assertIn('Error processing effect: Test error', result['errors'])

    def test_process_kill_buff_success(self):
        """Test successful kill_buff processing"""
        effect = {
            'stat_type': 'attack',
            'buff_type': 'flat',
            'value': 15,
            'target': 'self'
        }

        # Set up recipient unit
        self.recipient_unit.attack = 100

        result = self.processor._process_kill_buff(effect, [self.recipient_unit], {'processed': False, 'changes': {}, 'errors': []})

        self.assertTrue(result['processed'])
        self.assertIn('buffs_applied', result['changes'])
        # Check that attack was increased
        self.assertEqual(self.recipient_unit.attack, 115)  # 100 + 15

    def test_process_kill_buff_unknown_stat_type(self):
        """Test kill_buff with unknown stat type"""
        effect = {'stat_type': 'unknown_stat'}

        result = self.processor._process_kill_buff(effect, [self.recipient_unit], {'processed': False, 'changes': {}, 'errors': []})

        self.assertFalse(result['processed'])
        self.assertIn('Unknown stat type: unknown_stat', result['errors'])

    def test_process_kill_buff_handler_exception(self):
        """Test kill_buff when exception occurs"""
        effect = {'stat_type': 'attack', 'buff_type': 'flat', 'value': 10}

        # Set up unit without attack attribute to cause exception
        delattr(self.recipient_unit, 'attack')

        result = self.processor._process_kill_buff(effect, [self.recipient_unit], {'errors': []})

        self.assertTrue(result['processed'])  # Still processed, but with errors
        self.assertTrue(len(result['errors']) > 0)

    def test_process_collect_stat_initializes_collected_stats(self):
        """Test that collect_stat initializes collected_stats if needed"""
        effect = {'stat_type': 'defense'}

        # Create a fresh unit without collected_stats
        unit = Mock()
        unit.id = "test_unit"
        unit.name = "TestUnit"
        # Ensure no collected_stats attribute
        del unit.collected_stats  # This will raise AttributeError if it doesn't exist, but Mock handles it

        result = self.processor._process_collect_stat(effect, unit, {})

        self.assertTrue(result['processed'])
        self.assertTrue(hasattr(unit, 'collected_stats'))
        self.assertIn('defense', unit.collected_stats)
        self.assertEqual(unit.collected_stats['defense'], 0)

    def test_process_collect_stat_existing_collected_stats(self):
        """Test collect_stat with existing collected_stats"""
        effect = {'stat_type': 'attack'}

        # Unit already has collected_stats
        self.source_unit.collected_stats = {'kills': 2, 'attack': 50}

        result = self.processor._process_collect_stat(effect, self.source_unit, {})

        self.assertTrue(result['processed'])
        self.assertEqual(self.source_unit.collected_stats['attack'], 50)  # Unchanged

    def test_process_effect_with_recipient_resolution(self):
        """Test full effect processing with recipient resolution"""
        effect = {'action': 'kill_buff', 'stat_type': 'defense', 'value': 20}

        with patch.object(self.processor.recipient_resolver, 'find_recipients',
                         return_value=[self.recipient_unit]) as mock_find:
            with patch.object(self.processor, '_process_kill_buff',
                             return_value={'processed': True, 'changes': {'buffs_applied': []}}):
                result = self.processor.process_effect(
                    effect, self.source_unit, self.attacking_team,
                    self.defending_team, self.attacking_hp, self.defending_hp, 'team_a'
                )

                mock_find.assert_called_once_with(
                    self.source_unit, 'self', False,  # Default target='self', only_same_trait=False
                    self.attacking_team, self.defending_team, 'team_a'
                )
                self.assertTrue(result['processed'])

    def test_process_effect_no_recipients_found(self):
        """Test effect processing when no recipients found"""
        effect = {'action': 'kill_buff', 'stat_type': 'attack'}

        with patch.object(self.processor.recipient_resolver, 'find_recipients',
                         return_value=[]):
            result = self.processor.process_effect(
                effect, self.source_unit, self.attacking_team,
                self.defending_team, self.attacking_hp, self.defending_hp, 'team_a'
            )

            self.assertFalse(result['processed'])
            self.assertIn("No recipients found for target self", result['errors'])

    def test_buff_handlers_initialization(self):
        """Test that all expected buff handlers are initialized"""
        expected_handlers = ['attack', 'defense', 'hp', 'attack_speed', 'mana_regen']

        for stat_type in expected_handlers:
            self.assertIn(stat_type, self.processor.buff_handlers)
            self.assertIsNotNone(self.processor.buff_handlers[stat_type])


if __name__ == '__main__':
    unittest.main()