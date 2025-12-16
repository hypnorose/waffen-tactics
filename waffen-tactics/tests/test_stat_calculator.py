"""
Tests for StatCalculator utility class
"""
import unittest
from waffen_tactics.services.stat_calculator import StatCalculator


class TestStatCalculator(unittest.TestCase):
    """Test cases for StatCalculator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.calculator = StatCalculator()

    def test_calculate_buff_flat(self):
        """Test flat buff calculation"""
        result = self.calculator.calculate_buff(100, 25, False)
        self.assertEqual(result, 25)

    def test_calculate_buff_percentage(self):
        """Test percentage buff calculation"""
        result = self.calculator.calculate_buff(100, 50, True)
        self.assertEqual(result, 50)  # 100 * (50/100) = 50

    def test_calculate_buff_with_amplifier(self):
        """Test buff calculation with amplifier"""
        result = self.calculator.calculate_buff(100, 25, False, 2.0)
        self.assertEqual(result, 50)  # 25 * 2.0

    def test_calculate_buff_increment_flat_buff(self):
        """Test calculate_buff_increment with flat buff"""
        result = self.calculator.calculate_buff_increment(0, 25, 'flat')
        self.assertEqual(result, 25)

    def test_calculate_buff_increment_percentage_buff(self):
        """Test calculate_buff_increment with percentage buff"""
        result = self.calculator.calculate_buff_increment(0, 50, 'percentage', 100)
        self.assertEqual(result, 50)  # 100 * (50/100)

    def test_calculate_buff_increment_percentage_buff_no_base(self):
        """Test calculate_buff_increment with percentage buff but no base value"""
        result = self.calculator.calculate_buff_increment(0, 50, 'percentage', None)
        self.assertEqual(result, 0)

    def test_calculate_buff_increment_with_amplifier(self):
        """Test calculate_buff_increment with amplifier (should not apply amplifier)"""
        # Note: amplifiers are applied later in the effect processor
        result = self.calculator.calculate_buff_increment(0, 25, 'flat')
        self.assertEqual(result, 25)

    def test_calculate_buff_increment_invalid_buff_type(self):
        """Test calculate_buff_increment with invalid buff type"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_buff_increment(0, 25, 'invalid')

    def test_calculate_percentage_buff(self):
        """Test calculate_percentage_buff method"""
        result = self.calculator.calculate_percentage_buff(100, 50)
        self.assertEqual(result, 150)  # 100 * (1.0 + 50/100)

        result = self.calculator.calculate_percentage_buff(200, -25)
        self.assertEqual(result, 150)  # 200 * (1.0 + (-25)/100)

    def test_calculate_percentage_buff_with_amplifier(self):
        """Test percentage buff with amplifier"""
        result = self.calculator.calculate_percentage_buff(100, 50, 1.5)
        self.assertEqual(result, 175)  # 100 * (1.0 + (50/100) * 1.5)

    def test_get_buff_amplifier_no_effects(self):
        """Test buff amplifier with no effects"""
        effects = []
        result = self.calculator.get_buff_amplifier(effects)
        self.assertEqual(result, 1.0)

    def test_get_buff_amplifier_with_effects(self):
        """Test buff amplifier with buff amplifier effects"""
        effects = [
            {'type': 'buff_amplifier', 'multiplier': 1.5},
            {'type': 'other_effect'},
            {'type': 'buff_amplifier', 'multiplier': 2.0}
        ]
        result = self.calculator.get_buff_amplifier(effects)
        self.assertEqual(result, 3.0)  # 1.5 * 2.0

    def test_validate_stat_value_positive_stats(self):
        """Test validation of positive stats"""
        result = self.calculator.validate_stat_value(100, 'attack')
        self.assertEqual(result, 100)

        result = self.calculator.validate_stat_value(-5, 'defense')
        self.assertEqual(result, 0)  # Clamped to 0

    def test_validate_stat_value_special_stats(self):
        """Test validation allows negative for special stats"""
        result = self.calculator.validate_stat_value(-0.2, 'damage_reduction')
        self.assertEqual(result, -0.2)

        result = self.calculator.validate_stat_value(-0.1, 'lifesteal')
        self.assertEqual(result, -0.1)


if __name__ == '__main__':
    unittest.main()